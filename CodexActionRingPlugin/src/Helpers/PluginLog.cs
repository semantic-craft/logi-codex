namespace Loupedeck.CodexActionRingPlugin
{
    using System;

    // A helper class that enables logging from the plugin code.

    internal static class PluginLog
    {
        private static PluginLogFile _pluginLogFile;

        public static void Init(PluginLogFile pluginLogFile)
        {
            pluginLogFile.CheckNullArgument(nameof(pluginLogFile));
            PluginLog._pluginLogFile = pluginLogFile;
        }

        public static void Warning(String text) => PluginLog._pluginLogFile?.Warning(text);
    }
}
