#nullable enable

namespace Loupedeck.CodexActionRingPlugin.Logitech.Primary
{
    using System;
    using Loupedeck.CodexActionRingPlugin.Core;

    public abstract class PrimaryActionCommand : PluginDynamicCommand
    {
        private const String DefaultGroupName = "Codex Shortcut";

        private readonly RingActionId _actionId;
        private readonly PrimaryActionServices? _injectedServices;

        protected PrimaryActionCommand(RingActionId actionId)
            : base(
                PrimaryRingContract.GetDefinition(actionId).Label,
                $"Requests {PrimaryRingContract.GetDefinition(actionId).Label} through Codex Shortcut",
                PrimaryActionCommand.DefaultGroupName,
                DeviceType.LoupedeckExtendedFamily)
        {
            this._actionId = actionId;
        }

        internal PrimaryActionCommand(
            RingActionId actionId,
            IActionExecutor executor,
            IPrimaryFeedbackAdapter feedback)
            : this(actionId)
        {
            this._injectedServices = new PrimaryActionServices(
                executor ?? throw new ArgumentNullException(nameof(executor)),
                feedback ?? throw new ArgumentNullException(nameof(feedback)));
        }

        internal RingActionId ActionId => this._actionId;

        protected override void RunCommand(String actionParameter)
        {
            var services = this.ResolveServices();

            if (services is null)
            {
                return;
            }

            var result = services.Value.Executor.Execute(this._actionId);
            services.Value.Feedback.Present(this._actionId, result);
        }

        private PrimaryActionServices? ResolveServices()
        {
            if (this._injectedServices is not null)
            {
                return this._injectedServices;
            }

            if (this.Plugin is not IPrimaryActionDependencyProvider provider
                || provider.PrimaryActionExecutor is null
                || provider.PrimaryActionFeedback is null)
            {
                return null;
            }

            return new PrimaryActionServices(
                provider.PrimaryActionExecutor,
                provider.PrimaryActionFeedback);
        }
    }
}
