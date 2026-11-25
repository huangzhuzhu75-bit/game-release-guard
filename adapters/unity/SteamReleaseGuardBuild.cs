// Steam Release Guard - MIT. Unity 6 (6000.x), Windows x64 platform profile.
// This adapter is Editor-only. IL2CPP does not encrypt assets or prevent reverse engineering.
#if UNITY_EDITOR && UNITY_6000_0_OR_NEWER
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Profile;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace SteamReleaseGuard.Editor
{
    public static class ReleaseBuilder
    {
        internal static bool Building;
        internal const BuildOptions Forbidden = BuildOptions.Development | BuildOptions.AllowDebugging
            | BuildOptions.ConnectWithProfiler | BuildOptions.EnableDeepProfilingSupport
            | BuildOptions.IncludeTestAssemblies | BuildOptions.EnableCodeCoverage
            | BuildOptions.WaitForPlayerConnection;

        [MenuItem("Tools/Steam Release Guard/Build Windows Release")]
        public static void BuildWindows()
        {
            if (!Application.unityVersion.StartsWith("6000.", StringComparison.Ordinal))
                throw new BuildFailedException("This adapter targets Unity 6 (6000.x). Review other versions first.");
            // Never silently discard custom profile overrides or silently change the selected scene list.
            if (BuildProfile.GetActiveBuildProfile() != null)
                throw new BuildFailedException("Select the Windows platform profile (not a custom Build Profile) first. Custom overrides need a separate integration review.");
            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.StandaloneWindows64)
                throw new BuildFailedException("Switch to Windows x64 first, or launch Unity with -buildTarget Win64.");
            if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.Standalone, BuildTarget.StandaloneWindows64))
                throw new BuildFailedException("Windows build support is missing. Install the matching Windows IL2CPP module through Unity Hub.");
            var scenes = EditorBuildSettings.scenes.Where(scene => scene.enabled).Select(scene => scene.path).ToArray();
            if (scenes.Length == 0)
                throw new BuildFailedException("Enable the intended release scenes in the Windows platform profile first.");
            var output = CommandArgument("-srgOutput");
            if (string.IsNullOrEmpty(output))
            {
                if (Application.isBatchMode)
                    throw new BuildFailedException("Batch builds require -srgOutput <absolute path to Game.exe>.");
                var folder = EditorUtility.OpenFolderPanel("Choose a new empty release-build folder", "", "");
                if (string.IsNullOrEmpty(folder)) return;
                output = Path.Combine(folder, "Game.exe");
            }
            output = Path.GetFullPath(output);
            if (!output.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                throw new BuildFailedException("The Windows output must end in .exe.");
            var directory = Path.GetDirectoryName(output);
            if (Directory.Exists(directory) && Directory.EnumerateFileSystemEntries(directory).Any())
                throw new BuildFailedException("Choose a new empty output folder. Existing builds are never overwritten.");

            var target = NamedBuildTarget.Standalone;
            var previousBackend = PlayerSettings.GetScriptingBackend(target);
            var previousDevelopment = EditorUserBuildSettings.development;
            var previousDebugging = EditorUserBuildSettings.allowDebugging;
            var previousProfiler = EditorUserBuildSettings.connectProfiler;
            var previousDeepProfiling = EditorUserBuildSettings.buildWithDeepProfilingSupport;
            var previousSubtarget = EditorUserBuildSettings.standaloneBuildSubtarget;
            try
            {
                PlayerSettings.SetScriptingBackend(target, ScriptingImplementation.IL2CPP);
                EditorUserBuildSettings.development = false;
                EditorUserBuildSettings.allowDebugging = false;
                EditorUserBuildSettings.connectProfiler = false;
                EditorUserBuildSettings.buildWithDeepProfilingSupport = false;
                EditorUserBuildSettings.standaloneBuildSubtarget = StandaloneBuildSubtarget.Player;
                Building = true;
                var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = scenes,
                    locationPathName = output,
                    target = BuildTarget.StandaloneWindows64,
                    subtarget = (int)StandaloneBuildSubtarget.Player,
                    options = BuildOptions.StrictMode
                });
                if (report.summary.result != BuildResult.Succeeded)
                    throw new BuildFailedException("Release build failed. Read the Unity build log; verify IL2CPP modules, compiler and plugins.");
                if ((report.summary.options & Forbidden) != 0)
                    throw new BuildFailedException("Unexpected debug/test flags in the build report. Do not distribute this output.");
                Debug.Log("SRG: Windows x64 IL2CPP build completed without requested development/debug/test flags. "
                    + "Retain private symbols, audit the depot and test plugins, saves, multiplayer and developer shortcuts. Output: " + output);
            }
            finally
            {
                Building = false;
                PlayerSettings.SetScriptingBackend(target, previousBackend);
                EditorUserBuildSettings.development = previousDevelopment;
                EditorUserBuildSettings.allowDebugging = previousDebugging;
                EditorUserBuildSettings.connectProfiler = previousProfiler;
                EditorUserBuildSettings.buildWithDeepProfilingSupport = previousDeepProfiling;
                EditorUserBuildSettings.standaloneBuildSubtarget = previousSubtarget;
                AssetDatabase.SaveAssets();
            }
        }

        private static string CommandArgument(string name)
        {
            var args = Environment.GetCommandLineArgs();
            for (var i = 0; i < args.Length - 1; i++)
                if (args[i] == name) return args[i + 1];
            return null;
        }
    }

    // Validate just this adapter's builds. Normal developer workflows remain available.
    public sealed class ReleasePreflight : IPreprocessBuildWithReport
    {
        public int callbackOrder => int.MaxValue;
        public void OnPreprocessBuild(BuildReport report)
        {
            if (!ReleaseBuilder.Building) return;
            if ((report.summary.options & ReleaseBuilder.Forbidden) != 0
                || PlayerSettings.GetScriptingBackend(NamedBuildTarget.Standalone) != ScriptingImplementation.IL2CPP)
                throw new BuildFailedException("Release preflight rejected overridden debugging flags or a non-IL2CPP backend.");
        }
    }
}
#endif
