#nullable enable

namespace Loupedeck.CodexActionRingPlugin.Logitech.Primary
{
    using Loupedeck.CodexActionRingPlugin.Core;
    using Xunit;

    public sealed class PrimaryRingContractTests
    {
        private static readonly RingActionId[] ExpectedOrder =
        {
            RingActionId.NextAttention,
            RingActionId.ViewActivity,
            RingActionId.NewChat,
            RingActionId.QuickChat,
            RingActionId.SideChat,
            RingActionId.RecentlyViewed,
            RingActionId.CopyDeepLink,
            RingActionId.Dictation,
        };

        [Fact]
        public void PrimaryOrderMatchesTheLockedClockwiseContract()
        {
            Assert.Equal(PrimaryRingContractTests.ExpectedOrder, PrimaryRingContract.Order);
            Assert.Equal(
                PrimaryRingContractTests.ExpectedOrder.Append(RingActionId.SelectModel),
                PrimaryRingContract.Entries.Select(entry => entry.Id));
        }

        [Fact]
        public void AllEntriesMapToUniqueSdkActionsAndSemanticIconKeys()
        {
            var commands = PrimaryRingContract.Entries.ToArray();

            var expected = new[]
            {
                (RingActionId.NextAttention, "next_attention", "Loupedeck.CodexActionRingPlugin.Logitech.Primary.NextAttentionCommand"),
                (RingActionId.ViewActivity, "view_activity", "Loupedeck.CodexActionRingPlugin.Logitech.Primary.ViewActivityCommand"),
                (RingActionId.NewChat, "new_chat", "Loupedeck.CodexActionRingPlugin.Logitech.Primary.NewChatCommand"),
                (RingActionId.QuickChat, "quick_chat", "Loupedeck.CodexActionRingPlugin.Logitech.Primary.QuickChatCommand"),
                (RingActionId.SideChat, "side_chat", "Loupedeck.CodexActionRingPlugin.Logitech.Primary.SideChatCommand"),
                (RingActionId.RecentlyViewed, "recently_viewed", "Loupedeck.CodexActionRingPlugin.Logitech.Primary.RecentlyViewedCommand"),
                (RingActionId.CopyDeepLink, "copy_deep_link", "Loupedeck.CodexActionRingPlugin.Logitech.Primary.CopyDeepLinkCommand"),
                (RingActionId.Dictation, "dictation", "Loupedeck.CodexActionRingPlugin.Logitech.Primary.DictationCommand"),
                (RingActionId.SelectModel, "select_model", "Loupedeck.CodexActionRingPlugin.Logitech.Primary.SelectModelCommand"),
            };

            Assert.Equal(9, commands.Length);
            Assert.Equal(9, commands.Select(entry => entry.WrapperType).Distinct().Count());
            Assert.Equal(9, commands.Select(entry => entry.ActionName).Distinct().Count());
            Assert.Equal(
                expected,
                commands.Select(entry => (entry.Id, entry.IconKey, entry.ActionName)));

            foreach (var entry in commands)
            {
                Assert.True(typeof(PrimaryActionCommand).IsAssignableFrom(entry.WrapperType));
                Assert.Equal(entry.WrapperType.FullName, entry.ActionName);
                Assert.Equal(entry.StableId, entry.IconKey);
                Assert.DoesNotContain("Approve", entry.ActionName, StringComparison.OrdinalIgnoreCase);
                Assert.DoesNotContain("Decline", entry.ActionName, StringComparison.OrdinalIgnoreCase);
            }
        }

        [Fact]
        public void EntryMetadataComesFromTheCoreCatalog()
        {
            foreach (var entry in PrimaryRingContract.Entries)
            {
                Assert.True(RingActionCatalog.TryGetDefinition(entry.Id, out var definition));
                Assert.Equal(definition.StableId, entry.StableId);
                Assert.Equal(definition.Label, entry.Label);
                Assert.Equal(definition.IconKey, entry.IconKey);
            }
        }
    }
}
