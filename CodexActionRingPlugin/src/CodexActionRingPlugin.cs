namespace Loupedeck.CodexActionRingPlugin
{
    using System;
    using Loupedeck.CodexActionRingPlugin.Composition;
    using Loupedeck.CodexActionRingPlugin.Core;
    using Loupedeck.CodexActionRingPlugin.Logitech.Primary;

    // This class contains the plugin-level logic of the Loupedeck plugin.

    public sealed class CodexActionRingPlugin :
        Plugin,
        IPrimaryActionDependencyProvider
    {
        private readonly ActionRingComposition _composition;

        // Gets a value indicating whether this is an API-only plugin.
        public override Boolean UsesApplicationApiOnly => false;

        // Gets a value indicating whether this is a Universal plugin or an Application plugin.
        public override Boolean HasNoApplication => false;

        // Initializes a new instance of the plugin class.
        public CodexActionRingPlugin()
        {
            // Initialize the plugin log.
            PluginLog.Init(this.Log);

            this._composition = ActionRingComposition.CreateProduction(this);
        }

        public IActionExecutor PrimaryActionExecutor => this._composition.PrimaryActionExecutor;

        public IPrimaryFeedbackAdapter PrimaryActionFeedback => this._composition.PrimaryActionFeedback;

        // This method is called when the plugin is loaded.
        public override void Load()
        {
            this._composition.Load();
        }

        internal void NotifyActionImageChanged(String actionName, String actionParameter) =>
            this.OnActionImageChanged(actionName, actionParameter);
    }
}
