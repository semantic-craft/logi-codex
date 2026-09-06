#nullable enable

namespace Loupedeck.CodexActionRingPlugin.Core
{
    using System;

    [Flags]
    internal enum DesktopModifiers
    {
        None = 0,
        Command = 1,
        Control = 2,
        Option = 4,
        Shift = 8,
    }

    internal enum DesktopKey
    {
        A,
        D,
        N,
        U,
        S,
        L,
        Tab,
        M,
    }

    internal readonly record struct KeyboardShortcut(DesktopModifiers Modifiers, DesktopKey Key);

    internal enum DesktopInvocationKind
    {
        Shortcut,
        Uri,
    }

    internal readonly record struct DesktopInvocation
    {
        private DesktopInvocation(
            DesktopInvocationKind kind,
            KeyboardShortcut shortcut,
            Uri? uri)
        {
            this.Kind = kind;
            this.Shortcut = shortcut;
            this.Uri = uri;
        }

        internal DesktopInvocationKind Kind { get; }

        internal KeyboardShortcut Shortcut { get; }

        internal Uri? Uri { get; }

        internal static DesktopInvocation ForShortcut(DesktopModifiers modifiers, DesktopKey key) =>
            new(DesktopInvocationKind.Shortcut, new KeyboardShortcut(modifiers, key), null);

        internal static DesktopInvocation ForUri(String absoluteUri) =>
            new(DesktopInvocationKind.Uri, default, new Uri(absoluteUri, UriKind.Absolute));
    }

    internal enum ActionPrecondition
    {
        None,
        CodexFrontmost,
    }

    internal abstract record RingActionDelivery
    {
        private RingActionDelivery()
        {
        }

        internal sealed record Desktop(DesktopInvocation Invocation) : RingActionDelivery;
    }

    internal interface IDesktopBridge
    {
        DispatchResult Dispatch(DesktopInvocation invocation);
    }

    internal interface IActionPreconditionEvaluator
    {
        Boolean IsSatisfied(ActionPrecondition precondition);
    }
}
