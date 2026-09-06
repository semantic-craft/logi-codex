namespace Loupedeck.CodexActionRingPlugin.Core
{
    using System;
    using System.Collections.Generic;
    using System.Collections.ObjectModel;

    internal sealed record RingActionDefinition(
        RingActionId Id,
        String StableId,
        String Label,
        String IconKey,
        ActionPrecondition Precondition,
        RingActionDelivery Delivery);

    internal static class RingActionCatalog
    {
        private const DesktopModifiers Command = DesktopModifiers.Command;
        private const DesktopModifiers Control = DesktopModifiers.Control;
        private const DesktopModifiers Shift = DesktopModifiers.Shift;
        private const DesktopModifiers Option = DesktopModifiers.Option;

        private static readonly IReadOnlyList<RingActionDefinition> _definitions =
            Array.AsReadOnly(new[]
            {
                Shortcut(RingActionId.NextAttention, "next_attention", "Next Attention", Command | Option, DesktopKey.A),
                Shortcut(RingActionId.ViewActivity, "view_activity", "View Activity", Command | Option, DesktopKey.U),
                DeepLink(RingActionId.NewChat, "new_chat", "New Chat", "codex://threads/new"),
                Shortcut(RingActionId.QuickChat, "quick_chat", "Quick Chat", Command | Option, DesktopKey.N),
                Shortcut(RingActionId.SideChat, "side_chat", "Side Chat", Command | Option, DesktopKey.S),
                Shortcut(RingActionId.RecentlyViewed, "recently_viewed", "Recently Viewed", Control, DesktopKey.Tab),
                Shortcut(RingActionId.CopyDeepLink, "copy_deep_link", "Copy Deep Link", Command | Option, DesktopKey.L),
                Shortcut(RingActionId.Dictation, "dictation", "Start Dictation", Control | Shift, DesktopKey.D),
                Shortcut(RingActionId.SelectModel, "select_model", "Select Model", Control | Shift, DesktopKey.M),
            });

        private static readonly IReadOnlyDictionary<RingActionId, RingActionDefinition> _byId =
            BuildIndex(RingActionCatalog._definitions);

        private static readonly IReadOnlyList<RingActionId> _primaryOrder = Array.AsReadOnly(new[]
        {
            RingActionId.NextAttention,
            RingActionId.ViewActivity,
            RingActionId.NewChat,
            RingActionId.QuickChat,
            RingActionId.SideChat,
            RingActionId.RecentlyViewed,
            RingActionId.CopyDeepLink,
            RingActionId.Dictation,
        });

        internal static IReadOnlyList<RingActionDefinition> Definitions => RingActionCatalog._definitions;

        internal static IReadOnlyList<RingActionId> PrimaryOrder => RingActionCatalog._primaryOrder;

        internal static Boolean TryGetDefinition(RingActionId id, out RingActionDefinition definition) =>
            RingActionCatalog._byId.TryGetValue(id, out definition!);

        private static RingActionDefinition Shortcut(
            RingActionId id,
            String stableId,
            String label,
            DesktopModifiers modifiers,
            DesktopKey key) =>
            new(
                id,
                stableId,
                label,
                stableId,
                ActionPrecondition.CodexFrontmost,
                new RingActionDelivery.Desktop(DesktopInvocation.ForShortcut(modifiers, key)));

        private static RingActionDefinition DeepLink(
            RingActionId id,
            String stableId,
            String label,
            String uri) =>
            new(
                id,
                stableId,
                label,
                stableId,
                ActionPrecondition.CodexFrontmost,
                new RingActionDelivery.Desktop(DesktopInvocation.ForUri(uri)));

        private static ReadOnlyDictionary<RingActionId, RingActionDefinition> BuildIndex(
            IReadOnlyList<RingActionDefinition> definitions)
        {
            var index = new Dictionary<RingActionId, RingActionDefinition>(definitions.Count);

            foreach (var definition in definitions)
            {
                index.Add(definition.Id, definition);
            }

            return new ReadOnlyDictionary<RingActionId, RingActionDefinition>(index);
        }
    }
}
