#nullable enable

namespace Loupedeck.CodexActionRingPlugin.Logitech.Primary
{
    using System.Reflection;
    using Loupedeck.CodexActionRingPlugin.Core;
    using Xunit;

    public sealed class PrimaryActionCommandTests
    {
        public static IEnumerable<Object[]> Wrappers()
        {
            yield return Case(
                RingActionId.NextAttention,
                static (executor, feedback) => new NextAttentionCommand(executor, feedback));
            yield return Case(
                RingActionId.ViewActivity,
                static (executor, feedback) => new ViewActivityCommand(executor, feedback));
            yield return Case(
                RingActionId.NewChat,
                static (executor, feedback) => new NewChatCommand(executor, feedback));
            yield return Case(
                RingActionId.RecentlyViewed,
                static (executor, feedback) => new RecentlyViewedCommand(executor, feedback));
            yield return Case(
                RingActionId.QuickChat,
                static (executor, feedback) => new QuickChatCommand(executor, feedback));
            yield return Case(
                RingActionId.SelectModel,
                static (executor, feedback) => new SelectModelCommand(executor, feedback));
            yield return Case(
                RingActionId.Dictation,
                static (executor, feedback) => new DictationCommand(executor, feedback));
            yield return Case(
                RingActionId.SideChat,
                static (executor, feedback) => new SideChatCommand(executor, feedback));
            yield return Case(
                RingActionId.CopyDeepLink,
                static (executor, feedback) => new CopyDeepLinkCommand(executor, feedback));
        }

        [Theory]
        [MemberData(nameof(Wrappers))]
        public void EachWrapperDelegatesExactlyOnceAndForwardsUnchangedResult(
            RingActionId expectedId,
            Func<IActionExecutor, IPrimaryFeedbackAdapter, PrimaryActionCommand> create)
        {
            foreach (var result in Enum.GetValues<DispatchResult>())
            {
                var executor = new RecordingExecutor { Result = result };
                var feedback = new RecordingFeedbackAdapter();
                var command = create(executor, feedback);

                Assert.True(command.TryRunCommand(String.Empty));
                Assert.Equal(new[] { expectedId }, executor.Calls);
                Assert.Equal(new[] { (expectedId, result) }, feedback.Calls);
            }
        }

        [Theory]
        [MemberData(nameof(Wrappers))]
        public void EachWrapperIsAnAssignableExtendedFamilySdkAction(
            RingActionId expectedId,
            Func<IActionExecutor, IPrimaryFeedbackAdapter, PrimaryActionCommand> create)
        {
            var command = create(new RecordingExecutor(), new RecordingFeedbackAdapter());

            Assert.Equal(expectedId, command.ActionId);
            Assert.Equal(DeviceType.LoupedeckExtendedFamily, command.SupportedDevices);
            Assert.NotNull(command.GetType().GetConstructor(Type.EmptyTypes));
            Assert.True(command.GetType().IsSealed);
        }

        [Fact]
        public void WrappersOverrideOnlyTheSdkSelectionCallback()
        {
            var sdkOverrides = typeof(PrimaryActionCommand)
                .GetMethods(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly)
                .Where(method => method.GetBaseDefinition().DeclaringType != method.DeclaringType)
                .Select(method => method.Name)
                .ToArray();

            Assert.Equal(new[] { "RunCommand" }, sdkOverrides);
        }

        [Fact]
        public void SdkCanDiscoverEveryPublicWrapperBeforeCompositionAndResolveAtSelectionTime()
        {
            var commands = PrimaryRingContract.Entries
                .Select(entry => (entry.Id, Command: Assert.IsAssignableFrom<PrimaryActionCommand>(
                    Activator.CreateInstance(entry.WrapperType))))
                .ToArray();
            var executor = new RecordingExecutor();
            var feedback = new RecordingFeedbackAdapter();
            var plugin = new TestPlugin(executor, feedback);

            foreach (var (_, command) in commands)
            {
                SetSdkPlugin(command, plugin);
                Assert.True(command.TryRunCommand(String.Empty));
            }

            Assert.Equal(commands.Select(item => item.Id), executor.Calls);
            Assert.Equal(
                commands.Select(item => (item.Id, DispatchResult.DispatchRequested)),
                feedback.Calls);
        }

        [Fact]
        public void UncomposedSdkWrapperFailsClosedWithZeroDispatchAndFeedback()
        {
            var command = new NewChatCommand();

            Assert.True(command.TryRunCommand(String.Empty));
        }

        private static Object[] Case(
            RingActionId actionId,
            Func<IActionExecutor, IPrimaryFeedbackAdapter, PrimaryActionCommand> create) =>
            new Object[] { actionId, create };

        private static void SetSdkPlugin(PrimaryActionCommand command, Plugin plugin)
        {
            var pluginProperty = typeof(PluginDynamicAction).GetProperty(
                "Plugin",
                BindingFlags.Instance | BindingFlags.NonPublic);

            Assert.NotNull(pluginProperty);
            pluginProperty.SetValue(command, plugin);
        }
    }
}
