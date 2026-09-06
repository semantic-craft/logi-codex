#nullable enable

namespace Loupedeck.CodexActionRingPlugin.DesktopBridge.Tests
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using Loupedeck.CodexActionRingPlugin.Core;
    using Xunit;

    public sealed class CodexDesktopBridgeTests
    {
        private const String Version = "0.1.5";

        public static IEnumerable<Object[]> NonMatchingForegroundApplications()
        {
            yield return new Object[] { Array.Empty<FrontmostApplicationIdentity>() };
            yield return new Object[]
            {
                new[] { new FrontmostApplicationIdentity("Finder", "com.apple.finder") },
            };
            yield return new Object[]
            {
                new[] { new FrontmostApplicationIdentity("ChatGPT", "com.example.other") },
            };
            yield return new Object[]
            {
                new[] { new FrontmostApplicationIdentity("Other", "com.openai.codex") },
            };
            yield return new Object[]
            {
                new[] { new FrontmostApplicationIdentity("chatgpt", "com.openai.codex") },
            };
            yield return new Object[]
            {
                new[]
                {
                    new FrontmostApplicationIdentity("ChatGPT", "com.openai.codex"),
                    new FrontmostApplicationIdentity("ChatGPT", "com.openai.codex"),
                },
            };
        }

        [Theory]
        [MemberData(nameof(NonMatchingForegroundApplications))]
        internal void ShortcutFailsClosedUnlessForegroundIsAnUnambiguousExactMatch(
            IReadOnlyList<FrontmostApplicationIdentity> applications)
        {
            foreach (var definition in RingActionCatalog.Definitions)
            {
                var fixture = CreateFixture(applications);
                var invocation = ((RingActionDelivery.Desktop)definition.Delivery).Invocation;
                Assert.Equal(DispatchResult.NotDispatched, fixture.Bridge.Dispatch(invocation));
                Assert.Empty(fixture.Shortcuts.Shortcuts);
                Assert.Empty(fixture.DeepLinks.Uris);
                Assert.Single(fixture.Log.Entries);
            }
        }

        [Fact]
        internal void ForegroundQueryFailureSendsNothing()
        {
            var fixture = CreateFixture(CodexForeground());
            fixture.Frontmost.Exception = new InvalidOperationException("private detail");

            var result = fixture.Bridge.Dispatch(DesktopInvocation.ForShortcut(
                DesktopModifiers.Control,
                DesktopKey.Tab));

            Assert.Equal(DispatchResult.NotDispatched, result);
            Assert.Empty(fixture.Shortcuts.Shortcuts);
            Assert.Equal("foreground_query_failed", Assert.Single(fixture.Log.Entries).ErrorCategory);
        }

        [Fact]
        internal void EveryCatalogShortcutEncodingIsSentExactlyOnceUnchanged()
        {
            var shortcuts = RingActionCatalog.Definitions
                .Where(definition => definition.Delivery is RingActionDelivery.Desktop
                {
                    Invocation.Kind: DesktopInvocationKind.Shortcut,
                })
                .Select(definition => ((RingActionDelivery.Desktop)definition.Delivery).Invocation)
                .ToArray();

            Assert.Equal(8, shortcuts.Length);

            foreach (var invocation in shortcuts)
            {
                var fixture = CreateFixture(CodexForeground());

                var result = fixture.Bridge.Dispatch(invocation);

                Assert.Equal(DispatchResult.DispatchRequested, result);
                Assert.Equal(invocation.Shortcut, Assert.Single(fixture.Shortcuts.Shortcuts));
                Assert.Equal(1, fixture.Frontmost.Calls);
                Assert.Empty(fixture.DeepLinks.Uris);
            }
        }

        [Theory]
        [InlineData(LocalDispatchOutcome.Accepted, DispatchResult.DispatchRequested)]
        [InlineData(LocalDispatchOutcome.Rejected, DispatchResult.DispatchFailed)]
        [InlineData(LocalDispatchOutcome.AcceptanceUnknown, DispatchResult.OutcomeUnknown)]
        internal void ShortcutMapsOnlyLocallyObservableOutcomes(
            LocalDispatchOutcome localOutcome,
            DispatchResult expected)
        {
            var fixture = CreateFixture(CodexForeground());
            fixture.Shortcuts.Outcome = localOutcome;

            var result = fixture.Bridge.Dispatch(DesktopInvocation.ForShortcut(
                DesktopModifiers.Command | DesktopModifiers.Option,
                DesktopKey.A));

            Assert.Equal(expected, result);
            Assert.Single(fixture.Shortcuts.Shortcuts);
        }

        [Fact]
        internal void ShortcutExceptionIsOutcomeUnknownWithoutRetry()
        {
            var fixture = CreateFixture(CodexForeground());
            fixture.Shortcuts.Exception = new InvalidOperationException("workspace/private/task");

            var result = fixture.Bridge.Dispatch(DesktopInvocation.ForShortcut(
                DesktopModifiers.Control,
                DesktopKey.S));

            Assert.Equal(DispatchResult.OutcomeUnknown, result);
            Assert.Single(fixture.Shortcuts.Shortcuts);
            var entry = Assert.Single(fixture.Log.Entries);
            Assert.Equal(Version, entry.PluginVersion);
            Assert.Equal("dispatch_exception", entry.ErrorCategory);
            Assert.DoesNotContain("workspace", entry.ToString(), StringComparison.OrdinalIgnoreCase);
        }

        [Theory]
        [InlineData(LocalDispatchOutcome.Accepted, DispatchResult.DispatchRequested)]
        [InlineData(LocalDispatchOutcome.Rejected, DispatchResult.DispatchFailed)]
        [InlineData(LocalDispatchOutcome.AcceptanceUnknown, DispatchResult.OutcomeUnknown)]
        internal void NewChatUsesOnlyTheLockedDeepLink(
            LocalDispatchOutcome localOutcome,
            DispatchResult expected)
        {
            var fixture = CreateFixture(CodexForeground());
            fixture.DeepLinks.Outcome = localOutcome;

            var result = fixture.Bridge.Dispatch(DesktopInvocation.ForUri(CodexDesktopBridge.NewChatUri));

            Assert.Equal(expected, result);
            Assert.Equal(CodexDesktopBridge.NewChatUri, Assert.Single(fixture.DeepLinks.Uris).AbsoluteUri);
            Assert.Empty(fixture.Shortcuts.Shortcuts);
            Assert.Equal(1, fixture.Frontmost.Calls);
        }

        [Fact]
        internal void DeepLinkExceptionIsOutcomeUnknownWithoutFallbackOrRetry()
        {
            var fixture = CreateFixture(CodexForeground());
            fixture.DeepLinks.Exception = new InvalidOperationException("private URL failure detail");

            var result = fixture.Bridge.Dispatch(DesktopInvocation.ForUri(CodexDesktopBridge.NewChatUri));

            Assert.Equal(DispatchResult.OutcomeUnknown, result);
            Assert.Single(fixture.DeepLinks.Uris);
            Assert.Empty(fixture.Shortcuts.Shortcuts);
            Assert.Equal("dispatch_exception", Assert.Single(fixture.Log.Entries).ErrorCategory);
        }

        [Fact]
        internal void AnyOtherUriFailsClosedWithoutCommandNFallback()
        {
            var fixture = CreateFixture(CodexForeground());

            var result = fixture.Bridge.Dispatch(DesktopInvocation.ForUri("codex://threads/example"));

            Assert.Equal(DispatchResult.NotDispatched, result);
            Assert.Empty(fixture.DeepLinks.Uris);
            Assert.Empty(fixture.Shortcuts.Shortcuts);
            Assert.Equal("unsupported_uri", Assert.Single(fixture.Log.Entries).ErrorCategory);
        }

        [Theory]
        [InlineData(DispatchResult.NotDispatched)]
        [InlineData(DispatchResult.DispatchRequested)]
        [InlineData(DispatchResult.DispatchFailed)]
        [InlineData(DispatchResult.OutcomeUnknown)]
        internal void RecordingAdapterPreservesAllFourCoreResults(DispatchResult expected)
        {
            var adapter = new RecordingDesktopBridge { Result = expected };
            var invocation = DesktopInvocation.ForUri(CodexDesktopBridge.NewChatUri);

            var result = adapter.Dispatch(invocation);

            Assert.Equal(expected, result);
            Assert.Equal(invocation, Assert.Single(adapter.Invocations));
        }

        [Fact]
        internal void LoggingFailureDoesNotChangeDispatchResultOrCauseRetry()
        {
            var fixture = CreateFixture(CodexForeground());
            fixture.Shortcuts.Outcome = LocalDispatchOutcome.Rejected;
            fixture.Log.Exception = new InvalidOperationException("logging unavailable");

            var result = fixture.Bridge.Dispatch(DesktopInvocation.ForShortcut(
                DesktopModifiers.Control,
                DesktopKey.Tab));

            Assert.Equal(DispatchResult.DispatchFailed, result);
            Assert.Single(fixture.Shortcuts.Shortcuts);
            Assert.Single(fixture.Log.Entries);
        }

        [Theory]
        [InlineData("")]
        [InlineData("0.1")]
        [InlineData("workspace/private/task")]
        internal void PluginVersionCannotCarryPrivateText(String pluginVersion)
        {
            Assert.Throws<ArgumentException>(() => new CodexDesktopBridge(
                new StubFrontmostApplicationSource(),
                new RecordingShortcutDispatcher(),
                new RecordingDeepLinkDispatcher(),
                pluginVersion,
                new RecordingLogSink()));
        }

        private static BridgeFixture CreateFixture(
            IReadOnlyList<FrontmostApplicationIdentity> applications)
        {
            var frontmost = new StubFrontmostApplicationSource { Applications = applications };
            var shortcuts = new RecordingShortcutDispatcher();
            var deepLinks = new RecordingDeepLinkDispatcher();
            var log = new RecordingLogSink();
            var bridge = new CodexDesktopBridge(frontmost, shortcuts, deepLinks, Version, log);
            return new BridgeFixture(bridge, frontmost, shortcuts, deepLinks, log);
        }

        private static IReadOnlyList<FrontmostApplicationIdentity> CodexForeground() =>
            new[]
            {
                new FrontmostApplicationIdentity(
                    CodexFrontmostPolicy.ProcessName,
                    CodexFrontmostPolicy.BundleIdentifier),
            };

        private sealed record BridgeFixture(
            CodexDesktopBridge Bridge,
            StubFrontmostApplicationSource Frontmost,
            RecordingShortcutDispatcher Shortcuts,
            RecordingDeepLinkDispatcher DeepLinks,
            RecordingLogSink Log);
    }
}
