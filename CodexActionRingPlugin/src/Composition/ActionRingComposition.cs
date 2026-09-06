#nullable enable

namespace Loupedeck.CodexActionRingPlugin.Composition
{
    using System;
    using Loupedeck.CodexActionRingPlugin.Core;
    using Loupedeck.CodexActionRingPlugin.DesktopBridge;
    using Loupedeck.CodexActionRingPlugin.Logitech.Primary;

    internal sealed class ActionRingComposition : IPrimaryActionDependencyProvider
    {
        internal const String PluginVersion = "0.1.7";

        private readonly FeedbackCoordinator _feedback;
        private readonly HapticFeedbackAdapter _haptics;

        internal ActionRingComposition(CompositionPorts ports)
        {
            ArgumentNullException.ThrowIfNull(ports);

            var bridge = new CodexDesktopBridge(
                ports.FrontmostApplications,
                ports.Shortcuts,
                ports.DeepLinks,
                PluginVersion,
                ports.Log);
            var executor = new ActionExecutor(
                bridge,
                new CodexFrontmostPreconditionEvaluator(ports.FrontmostApplications));

            this._haptics = new HapticFeedbackAdapter(ports.Haptics);
            this._feedback = new FeedbackCoordinator(ports.Images, this._haptics);
            this.PrimaryActionExecutor = executor;
            this.PrimaryActionFeedback = this._feedback;
        }

        public IActionExecutor PrimaryActionExecutor { get; }

        public IPrimaryFeedbackAdapter PrimaryActionFeedback { get; }

        internal void Load() => this._haptics.RegisterAll();

        internal static ActionRingComposition CreateProduction(CodexActionRingPlugin plugin)
        {
            ArgumentNullException.ThrowIfNull(plugin);

            var workspace = new MacOsWorkspaceAdapter();
            return new ActionRingComposition(new CompositionPorts(
                workspace,
                new LogitechShortcutDispatcher((key, modifiers) =>
                    plugin.ClientApplication.SendKeyboardShortcut(key, modifiers)),
                workspace,
                new PluginDesktopBridgeLogSink(),
                new LogitechActionImageInvalidator(plugin),
                new LogitechHapticEventSink(() => plugin.PluginEvents)));
        }
    }
}
