// Steam Release Guard - MIT. Obfuz 4.0.0, Unity 6000.x. Editor only.
// No engine patches, key creation, metadata encryption or runtime approval.
#if UNITY_EDITOR && UNITY_6000_0_OR_NEWER
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using dnlib.DotNet;
using Obfuz.ObfusPasses;
using Obfuz.Settings;
using Obfuz.Unity;
using UnityEditor;
using UnityEditor.Build;
using UnityEngine;

namespace SteamReleaseGuard.Advanced
{
    public static class ObfuscatedBuild
    {
        [Serializable] public class AssemblySelection
        {
            public string name;
            public string[] include_types;
            public string[] exclude_types;
            public bool rename_fields;
        }
        [Serializable] public class Configuration
        {
            public int schema;
            public string engine_version, adapter, tool_version;
            public AssemblySelection[] assemblies;
            public string[] reference_assemblies;
            public bool strings, control_flow;
        }
        [Serializable] public class AssemblyEvidence
        {
            public string name, before_sha256, after_sha256;
            public int renamed_selected_types;
        }
        [Serializable] public class Receipt
        {
            public string configuration = "PASS", artifact = "PASS", runtime = "NOT_VERIFIED";
            public string engine_version, tool_version, executable_sha256;
            public AssemblyEvidence[] assemblies;
        }

        private static string Argument(string key)
        {
            var args = Environment.GetCommandLineArgs();
            var i = Array.IndexOf(args, key);
            if (i < 0 || i + 1 >= args.Length || string.IsNullOrWhiteSpace(args[i + 1]))
                throw new BuildFailedException("Missing explicit build output/evidence argument.");
            return Path.GetFullPath(args[i + 1]);
        }

        private static string Hash(string path)
        {
            using (var hash = SHA256.Create())
            using (var input = File.OpenRead(path))
                return BitConverter.ToString(hash.ComputeHash(input)).Replace("-", "").ToLowerInvariant();
        }

        private static bool Excluded(string name, string[] exclusions)
        {
            return exclusions.Any(p => p.EndsWith("*", StringComparison.Ordinal)
                ? name.StartsWith(p.Substring(0, p.Length - 1), StringComparison.Ordinal) : name == p);
        }

        public static void BuildWindows()
        {
            const string configPath = "ProjectSettings/SteamReleaseGuardObfuscation.json";
            const string settingsPath = "ProjectSettings/Obfuz.asset";
            var config = JsonUtility.FromJson<Configuration>(File.ReadAllText(configPath));
            if (config.schema != 1 || config.adapter != "obfuz" || config.tool_version != "4.0.0" ||
                config.engine_version != Application.unityVersion || config.strings || config.control_flow ||
                config.assemblies == null || config.assemblies.Length == 0)
                throw new BuildFailedException("Unsupported obfuscation configuration or exact Editor version mismatch.");
            var package = UnityEditor.PackageManager.PackageInfo.FindForAssembly(typeof(ObfuzSettings).Assembly);
            if (package == null || package.name != "com.code-philosophy.obfuz" || package.version != "4.0.0")
                throw new BuildFailedException("The Editor did not resolve reviewed Obfuz 4.0.0.");
            if (!File.Exists(settingsPath))
                throw new BuildFailedException("Configure Obfuz yourself first. SRG does not create keys or a VM.");
            var evidence = Argument("-srgEvidence");
            var output = Argument("-srgOutput");
            if (!Directory.Exists(evidence) || File.Exists(Path.Combine(evidence, "obfuscation.json")) ||
                File.Exists(Path.Combine(evidence, "symbol-mapping.xml")))
                throw new BuildFailedException("Use a new private evidence directory.");
            var settingsBytes = File.ReadAllBytes(settingsPath);
            var settings = ObfuzSettings.Instance;
            var saved = EditorJsonUtility.ToJson(settings);
            if (settings.encryptionVMSettings == null || !File.Exists(settings.encryptionVMSettings.codeOutputPath))
                throw new BuildFailedException("Obfuz's existing generated VM is required even for symbol-only builds. Set it up and review it first.");
            var rows = new List<AssemblyEvidence>();
            bool completed = false;
            Action<ObfuscationEndEventArgs> onEnd = args =>
            {
                if (!args.success) throw new BuildFailedException("Obfuz failed; refusing to approve this build.");
                foreach (var selection in config.assemblies)
                {
                    var before = Path.Combine(args.originalScriptAssembliesPath, selection.name + ".dll");
                    var after = Path.Combine(args.obfuscatedScriptAssembliesPath, selection.name + ".dll");
                    if (!File.Exists(before) || !File.Exists(after))
                        throw new BuildFailedException("Obfuscation output/backup assembly missing.");
                    int changed = 0;
                    // dnlib validates actual managed metadata; no Assembly.Load of game code.
                    using (var original = ModuleDefMD.Load(before))
                    using (var obfuscated = ModuleDefMD.Load(after))
                    {
                        if (original.Assembly.Name != obfuscated.Assembly.Name)
                            throw new BuildFailedException("Unexpected assembly identity change.");
                        var oldTypes = new HashSet<string>(original.GetTypes().Select(t => t.FullName));
                        var newTypes = new HashSet<string>(obfuscated.GetTypes().Select(t => t.FullName));
                        foreach (var type in selection.include_types)
                        {
                            if (Excluded(type, selection.exclude_types)) continue;
                            if (!oldTypes.Contains(type)) throw new BuildFailedException("Selected type missing from original player assembly.");
                            if (!newTypes.Contains(type)) changed++;
                        }
                        // Excluded concrete types that existed must keep their names.
                        foreach (var type in oldTypes.Where(n => Excluded(n, selection.exclude_types)))
                            if (!newTypes.Contains(type)) throw new BuildFailedException("Excluded type was renamed.");
                    }
                    if (changed == 0 || Hash(before) == Hash(after))
                        throw new BuildFailedException("No selected-type rename evidence. Choose eligible types; Unity/serialization rules may preserve names.");
                    rows.Add(new AssemblyEvidence { name = selection.name, before_sha256 = Hash(before),
                        after_sha256 = Hash(after), renamed_selected_types = changed });
                }
                completed = true;
            };
            try
            {
                settings.buildPipelineSettings.enable = true;
                settings.assemblySettings.assembliesToObfuscate = config.assemblies.Select(a => a.name).ToArray();
                settings.assemblySettings.nonObfuscatedButReferencingObfuscatedAssemblies = config.reference_assemblies;
                settings.assemblySettings.obfuscateObfuzRuntime = false;
                settings.obfuscationPassSettings.enabledPasses = ObfuscationPassType.SymbolObfus;
                settings.obfuscationPassSettings.ruleFiles = Array.Empty<string>();
                settings.symbolObfusSettings.debug = false;
                settings.symbolObfusSettings.detectReflectionCompatibility = true;
                settings.symbolObfusSettings.customRenamePolicyTypes = Array.Empty<string>();
                settings.symbolObfusSettings.ruleFiles = new[] { "Assets/SteamReleaseGuard/AdvancedEditor/rename.xml" };
                settings.symbolObfusSettings.symbolMappingFile = Path.Combine(evidence, "symbol-mapping.xml");
                ObfuscationProcess.OnObfuscationEnd += onEnd;
                SteamReleaseGuard.Editor.ReleaseBuilder.BuildWindows();
                if (!completed || !File.Exists(output))
                    throw new BuildFailedException("Missing Obfuz event or game executable. Incremental build is not fresh evidence.");
                var receipt = new Receipt { engine_version = Application.unityVersion, tool_version = package.version,
                    executable_sha256 = Hash(output), assemblies = rows.ToArray() };
                File.WriteAllText(Path.Combine(evidence, "obfuscation.json"), JsonUtility.ToJson(receipt, true));
            }
            finally
            {
                ObfuscationProcess.OnObfuscationEnd -= onEnd;
                EditorJsonUtility.FromJsonOverwrite(saved, settings);
                File.WriteAllBytes(settingsPath, settingsBytes);
            }
        }
    }
}
#endif
