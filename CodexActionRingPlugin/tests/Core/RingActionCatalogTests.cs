namespace Loupedeck.CodexActionRingPlugin.Core.Tests
{
    using System;
    using System.Linq;
    using Loupedeck.CodexActionRingPlugin.Core;
    using Xunit;

    public sealed class RingActionCatalogTests
    {
        [Fact]
        public void CatalogContainsTheExactLockedStaticMetadata()
        {
            var expected = new[]
            {
                Metadata(RingActionId.NextAttention, "next_attention", "Next Attention"),
                Metadata(RingActionId.ViewActivity, "view_activity", "View Activity"),
                Metadata(RingActionId.NewChat, "new_chat", "New Chat"),
                Metadata(RingActionId.QuickChat, "quick_chat", "Quick Chat"),
                Metadata(RingActionId.SideChat, "side_chat", "Side Chat"),
                Metadata(RingActionId.RecentlyViewed, "recently_viewed", "Recently Viewed"),
                Metadata(RingActionId.CopyDeepLink, "copy_deep_link", "Copy Deep Link"),
                Metadata(RingActionId.Dictation, "dictation", "Start Dictation"),
                Metadata(RingActionId.SelectModel, "select_model", "Select Model"),
            };

            var actual = RingActionCatalog.Definitions.Select(definition =>
                new ExpectedMetadata(definition.Id, definition.StableId, definition.Label, definition.IconKey));

            Assert.Equal(expected, actual);
        }

        [Fact]
        public void ExecutorResolvesTheExactLockedDeliveryMappings()
        {
            var expected = new[]
            {
                Shortcut(RingActionId.NextAttention, DesktopModifiers.Command | DesktopModifiers.Option, DesktopKey.A),
                Shortcut(RingActionId.ViewActivity, DesktopModifiers.Command | DesktopModifiers.Option, DesktopKey.U),
                DeepLink(RingActionId.NewChat, "codex://threads/new"),
                Shortcut(RingActionId.QuickChat, DesktopModifiers.Command | DesktopModifiers.Option, DesktopKey.N),
                Shortcut(RingActionId.SideChat, DesktopModifiers.Command | DesktopModifiers.Option, DesktopKey.S),
                Shortcut(RingActionId.RecentlyViewed, DesktopModifiers.Control, DesktopKey.Tab),
                Shortcut(RingActionId.CopyDeepLink, DesktopModifiers.Command | DesktopModifiers.Option, DesktopKey.L),
                Shortcut(RingActionId.Dictation, DesktopModifiers.Control | DesktopModifiers.Shift, DesktopKey.D),
                Shortcut(RingActionId.SelectModel, DesktopModifiers.Control | DesktopModifiers.Shift, DesktopKey.M),
            };

            foreach (var delivery in expected)
            {
                var bridge = new RecordingDesktopBridge();
                var preconditions = new RecordingPreconditionEvaluator();
                IActionExecutor executor = new ActionExecutor(bridge, preconditions);

                var result = executor.Execute(delivery.ActionId);

                var invocation = Assert.Single(bridge.Invocations);
                Assert.Equal(DispatchResult.DispatchRequested, result);
                Assert.Equal(delivery.InvocationKind, invocation.Kind);

                if (delivery.InvocationKind == DesktopInvocationKind.Uri)
                {
                    Assert.Equal(delivery.Uri, invocation.Uri!.AbsoluteUri);
                }
                else
                {
                    Assert.Equal(new KeyboardShortcut(delivery.Modifiers, delivery.Key), invocation.Shortcut);
                }
            }
        }

        [Fact]
        public void CatalogHasExactlyNineUniqueIdsAndIconKeys()
        {
            Assert.Equal(9, RingActionCatalog.Definitions.Count);
            Assert.Equal(9, Enum.GetValues<RingActionId>().Length);
            Assert.Equal(9, RingActionCatalog.Definitions.Select(definition => definition.Id).Distinct().Count());
            Assert.Equal(9, RingActionCatalog.Definitions.Select(definition => definition.StableId).Distinct(StringComparer.Ordinal).Count());
            Assert.Equal(9, RingActionCatalog.Definitions.Select(definition => definition.IconKey).Distinct(StringComparer.Ordinal).Count());
            Assert.All(RingActionCatalog.Definitions, definition => Assert.Equal(definition.StableId, definition.IconKey));
        }

        [Fact]
        public void PrimaryOrderIsFixedClockwiseFromTheTop()
        {
            Assert.Equal(
                new[]
                {
                    RingActionId.NextAttention,
                    RingActionId.ViewActivity,
                    RingActionId.NewChat,
                    RingActionId.QuickChat,
                    RingActionId.SideChat,
                    RingActionId.RecentlyViewed,
                    RingActionId.CopyDeepLink,
                    RingActionId.Dictation,
                },
                RingActionCatalog.PrimaryOrder);
        }

        [Fact]
        public void ApprovalActionsCannotBeRepresented()
        {
            var names = Enum.GetNames<RingActionId>();
            var stableIds = RingActionCatalog.Definitions.Select(definition => definition.StableId);

            Assert.DoesNotContain(names, name => String.Equals(name, "Approve", StringComparison.OrdinalIgnoreCase));
            Assert.DoesNotContain(names, name => String.Equals(name, "Decline", StringComparison.OrdinalIgnoreCase));
            Assert.DoesNotContain(stableIds, id => id.Contains("approve", StringComparison.OrdinalIgnoreCase));
            Assert.DoesNotContain(stableIds, id => id.Contains("decline", StringComparison.OrdinalIgnoreCase));
        }

        private static ExpectedMetadata Metadata(RingActionId id, String stableId, String label) =>
            new(id, stableId, label, stableId);

        private static ExpectedDelivery Shortcut(
            RingActionId id,
            DesktopModifiers modifiers,
            DesktopKey key) =>
            new(id, DesktopInvocationKind.Shortcut, modifiers, key, null);

        private static ExpectedDelivery DeepLink(RingActionId id, String uri) =>
            new(id, DesktopInvocationKind.Uri, DesktopModifiers.None, default, uri);

        private sealed record ExpectedMetadata(
            RingActionId Id,
            String StableId,
            String Label,
            String IconKey);

        private sealed record ExpectedDelivery(
            RingActionId ActionId,
            DesktopInvocationKind InvocationKind,
            DesktopModifiers Modifiers,
            DesktopKey Key,
            String? Uri);
    }
}
