#nullable enable

namespace Loupedeck.CodexActionRingPlugin.Integration.Tests
{
    using System;
    using System.Collections.Generic;
    using System.IO;
    using System.Linq;
    using System.Reflection;
    using Loupedeck.CodexActionRingPlugin.Composition;
    using Loupedeck.CodexActionRingPlugin.Core;
    using Loupedeck.CodexActionRingPlugin.DesktopBridge;
    using Loupedeck.CodexActionRingPlugin.Feedback;
    using Loupedeck.CodexActionRingPlugin.Logitech.Primary;
    using Xunit;

    public sealed class CompositionIntegrationTests
    {
        [Fact]
        public void CompositionExposesThePrimaryExecutorAndFeedback()
        {
            var fixture = new IntegrationFixture();

            Assert.NotNull(fixture.Composition.PrimaryActionExecutor);
            Assert.NotNull(fixture.Composition.PrimaryActionFeedback);
        }

        [Fact]
        public void CompleteEightActionCatalogFlowsThroughTheSingleExecutorWithoutFallback()
        {
            var fixture = new IntegrationFixture();
            var results = RingActionCatalog.Definitions.ToDictionary(
                definition => definition.Id,
                definition => fixture.Composition.PrimaryActionExecutor.Execute(definition.Id));

            Assert.Equal(8, results.Count);
            Assert.All(results.Values, result => Assert.Equal(DispatchResult.DispatchRequested, result));
            Assert.Equal(7, fixture.Shortcuts.Calls.Count);
            Assert.Equal("codex://threads/new", Assert.Single(fixture.DeepLinks.Calls).AbsoluteUri);
        }

        [Fact]
        public void AllShortcutEncodingIsSentExactlyOnceUnchanged()
        {
            var sent = new List<(VirtualKeyCode Key, ModifierKey Modifiers)>();
            var adapter = new LogitechShortcutDispatcher((key, modifiers) =>
                sent.Add((key, modifiers)));

            foreach (var definition in RingActionCatalog.Definitions)
            {
                if (definition.Delivery is RingActionDelivery.Desktop
                    {
                        Invocation.Kind: DesktopInvocationKind.Shortcut
                    } desktop)
                {
                    Assert.Equal(
                        LocalDispatchOutcome.Accepted,
                        adapter.Dispatch(desktop.Invocation.Shortcut));
                }
            }

            Assert.Equal(
                new[]
                {
                    (VirtualKeyCode.KeyA, ModifierKey.Command | ModifierKey.AltOrOption),
                    (VirtualKeyCode.KeyU, ModifierKey.Command | ModifierKey.AltOrOption),
                    (VirtualKeyCode.KeyN, ModifierKey.Command | ModifierKey.AltOrOption),
                    (VirtualKeyCode.KeyS, ModifierKey.Command | ModifierKey.AltOrOption),
                    (VirtualKeyCode.Tab, ModifierKey.Ctrl),
                    (VirtualKeyCode.KeyL, ModifierKey.Command | ModifierKey.AltOrOption),
                    (VirtualKeyCode.KeyD, ModifierKey.Ctrl | ModifierKey.Shift),
                },
                sent);
        }

        [Fact]
        public void HostDiscoverySurfaceContainsOnlyEightPrimaryCommands()
        {
            var plugin = new CodexActionRingPlugin();
            var provider = Assert.IsAssignableFrom<IPrimaryActionDependencyProvider>(plugin);
            Assert.NotNull(provider.PrimaryActionExecutor);

            var assembly = typeof(CodexActionRingPlugin).Assembly;
            Assert.Equal(
                8,
                assembly.GetTypes().Count(type =>
                    type.IsPublic
                    && type.IsSealed
                    && typeof(PrimaryActionCommand).IsAssignableFrom(type)));
            Assert.DoesNotContain(
                assembly.GetTypes(),
                type => !type.IsAbstract && typeof(PluginDynamicFolder).IsAssignableFrom(type));

            var application = new CodexActionRingApplication();
            Assert.Equal("ChatGPT", InvokeProtectedString(application, "GetProcessName"));
            Assert.Equal("com.openai.codex", InvokeProtectedString(application, "GetBundleName"));
        }

        [Fact]
        public void HapticRegistrationRaisingAndSourceAssetsUseTheSameExactNames()
        {
            var fixture = new IntegrationFixture();
            fixture.Composition.Load();

            Assert.Equal(
                HapticEventNames.All.Order(),
                fixture.Haptics.Registrations.Select(definition => definition.Name).Order());

            var feedback = fixture.Composition.PrimaryActionFeedback;
            feedback.Present(RingActionId.RecentlyViewed, DispatchResult.NotDispatched);
            feedback.Present(RingActionId.RecentlyViewed, DispatchResult.DispatchRequested);
            feedback.Present(RingActionId.RecentlyViewed, DispatchResult.DispatchFailed);

            Assert.Equal(
                new[]
                {
                    HapticEventNames.SelectionRejected,
                    HapticEventNames.DispatchRequested,
                    HapticEventNames.DispatchFailed,
                },
                fixture.Haptics.Raised);

            var eventSource = File.ReadAllText(
                Path.Combine(AppContext.BaseDirectory, "assets", "haptics", "DefaultEventSource.yaml"));
            var eventMapping = File.ReadAllText(
                Path.Combine(AppContext.BaseDirectory, "assets", "haptics", "extra", "eventMapping.yaml"));
            foreach (var eventName in HapticEventNames.All)
            {
                Assert.Contains($"name: {eventName}", eventSource, StringComparison.Ordinal);
                Assert.Contains($"  {eventName}:", eventMapping, StringComparison.Ordinal);
            }
        }

        [Fact]
        public void PrimaryFeedbackRealizesOnlyEvidenceBackedImageAndHapticEffects()
        {
            var fixture = new IntegrationFixture();
            var feedback = fixture.Composition.PrimaryActionFeedback;

            foreach (var result in Enum.GetValues<DispatchResult>())
            {
                feedback.Present(RingActionId.RecentlyViewed, result);
            }

            Assert.Equal(
                Enumerable.Repeat(RingActionId.RecentlyViewed, 4),
                fixture.Images.Primary);
            Assert.Equal(
                new[]
                {
                    HapticEventNames.SelectionRejected,
                    HapticEventNames.DispatchRequested,
                    HapticEventNames.DispatchFailed,
                },
                fixture.Haptics.Raised);
        }

        [Fact]
        public void PrimaryFeedbackFailuresNeverEscapeOrRetryDispatchEffects()
        {
            var fixture = new IntegrationFixture();
            fixture.Images.ThrowOnPrimary = true;
            fixture.Haptics.ThrowOnRaise = true;

            var exception = Record.Exception(() => fixture.Composition.PrimaryActionFeedback.Present(
                RingActionId.RecentlyViewed,
                DispatchResult.DispatchFailed));

            Assert.Null(exception);
            Assert.Equal(new[] { RingActionId.RecentlyViewed }, fixture.Images.Primary);
            Assert.Equal(new[] { HapticEventNames.DispatchFailed }, fixture.Haptics.Raised);
        }

        [Fact]
        public void DesktopLogFormattingContainsOnlyVersionAndAnonymousCategory()
        {
            var text = PluginDesktopBridgeLogSink.Format(
                new DesktopBridgeLogEntry("0.1.5", "foreground_mismatch"));

            Assert.Equal("0.1.5 foreground_mismatch", text);
            Assert.DoesNotContain("/", text, StringComparison.Ordinal);
            Assert.DoesNotContain("prompt", text, StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain("task", text, StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain("credential", text, StringComparison.OrdinalIgnoreCase);
        }

        private static String InvokeProtectedString(Object target, String methodName)
        {
            var method = target.GetType().GetMethod(
                methodName,
                BindingFlags.Instance | BindingFlags.NonPublic);
            Assert.NotNull(method);
            return Assert.IsType<String>(method.Invoke(target, null));
        }
    }
}
