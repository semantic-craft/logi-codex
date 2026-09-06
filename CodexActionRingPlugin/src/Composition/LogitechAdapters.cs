#nullable enable

namespace Loupedeck.CodexActionRingPlugin.Composition
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    using Loupedeck.CodexActionRingPlugin.Core;
    using Loupedeck.CodexActionRingPlugin.DesktopBridge;
    using Loupedeck.CodexActionRingPlugin.Feedback;
    using Loupedeck.CodexActionRingPlugin.Logitech.Primary;

    internal sealed class LogitechShortcutDispatcher : IShortcutDispatcher
    {
        private readonly Action<VirtualKeyCode, ModifierKey> _send;

        internal LogitechShortcutDispatcher(Action<VirtualKeyCode, ModifierKey> send)
        {
            this._send = send ?? throw new ArgumentNullException(nameof(send));
        }

        public LocalDispatchOutcome Dispatch(KeyboardShortcut shortcut)
        {
            this._send(MapKey(shortcut.Key), MapModifiers(shortcut.Modifiers));
            return LocalDispatchOutcome.Accepted;
        }

        private static VirtualKeyCode MapKey(DesktopKey key) => key switch
        {
            DesktopKey.A => VirtualKeyCode.KeyA,
            DesktopKey.U => VirtualKeyCode.KeyU,
            DesktopKey.L => VirtualKeyCode.KeyL,
            DesktopKey.D => VirtualKeyCode.KeyD,
            DesktopKey.N => VirtualKeyCode.KeyN,
            DesktopKey.Tab => VirtualKeyCode.Tab,
            DesktopKey.S => VirtualKeyCode.KeyS,
            DesktopKey.M => VirtualKeyCode.KeyM,
            _ => throw new ArgumentOutOfRangeException(nameof(key), key, "Unsupported shortcut key."),
        };

        private static ModifierKey MapModifiers(DesktopModifiers modifiers)
        {
            const DesktopModifiers known = DesktopModifiers.Command
                | DesktopModifiers.Control
                | DesktopModifiers.Option
                | DesktopModifiers.Shift;

            if ((modifiers & ~known) != DesktopModifiers.None)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(modifiers),
                    modifiers,
                    "Unsupported shortcut modifier.");
            }

            var mapped = ModifierKey.None;
            if (modifiers.HasFlag(DesktopModifiers.Command))
            {
                mapped |= ModifierKey.Command;
            }

            if (modifiers.HasFlag(DesktopModifiers.Control))
            {
                mapped |= ModifierKey.Ctrl;
            }

            if (modifiers.HasFlag(DesktopModifiers.Option))
            {
                mapped |= ModifierKey.AltOrOption;
            }

            if (modifiers.HasFlag(DesktopModifiers.Shift))
            {
                mapped |= ModifierKey.Shift;
            }

            return mapped;
        }
    }

    internal sealed class PluginDesktopBridgeLogSink : IDesktopBridgeLogSink
    {
        public void Write(DesktopBridgeLogEntry entry) => PluginLog.Warning(Format(entry));

        internal static String Format(DesktopBridgeLogEntry entry) =>
            $"{entry.PluginVersion} {entry.ErrorCategory}";
    }

    internal sealed class LogitechHapticEventSink : IHapticEventSink
    {
        private readonly Func<PluginEventSender> _sender;
        private readonly HashSet<String> _registered = new(StringComparer.Ordinal);

        internal LogitechHapticEventSink(Func<PluginEventSender> sender)
        {
            this._sender = sender ?? throw new ArgumentNullException(nameof(sender));
        }

        public void Register(HapticEventDefinition definition)
        {
            if (this._registered.Contains(definition.Name))
            {
                return;
            }

            this._sender().AddEvent(
                definition.Name,
                definition.DisplayName,
                definition.Description);
            this._registered.Add(definition.Name);
        }

        public void Raise(String eventName) => this._sender().RaiseEvent(eventName);
    }

    internal sealed class LogitechActionImageInvalidator : IActionImageInvalidator
    {
        private static readonly IReadOnlyDictionary<RingActionId, String> _primaryActionNames =
            PrimaryRingContract.Entries
                .ToDictionary(entry => entry.Id, entry => entry.ActionName);

        private readonly CodexActionRingPlugin _plugin;

        internal LogitechActionImageInvalidator(CodexActionRingPlugin plugin)
        {
            this._plugin = plugin ?? throw new ArgumentNullException(nameof(plugin));
        }

        public void PrimaryProjectionChanged(RingActionId actionId)
        {
            if (_primaryActionNames.TryGetValue(actionId, out var actionName))
            {
                this._plugin.NotifyActionImageChanged(actionName, String.Empty);
            }
        }
    }

    internal sealed class HapticFeedbackAdapter
    {
        internal static IReadOnlyList<HapticEventDefinition> Definitions { get; } =
            Array.AsReadOnly(new[]
            {
                new HapticEventDefinition(
                    HapticEventNames.DispatchRequested,
                    "Dispatch Requested",
                    "A local delivery request was accepted; the Codex outcome is unknown."),
                new HapticEventDefinition(
                    HapticEventNames.DispatchFailed,
                    "Dispatch Failed",
                    "The local delivery adapter synchronously rejected or failed the request."),
                new HapticEventDefinition(
                    HapticEventNames.SelectionRejected,
                    "Selection Rejected",
                    "A selection-time availability race prevented local delivery."),
            });

        private readonly IHapticEventSink _events;

        internal HapticFeedbackAdapter(IHapticEventSink events)
        {
            this._events = events ?? throw new ArgumentNullException(nameof(events));
        }

        internal void RegisterAll()
        {
            foreach (var definition in Definitions)
            {
                this._events.Register(definition);
            }
        }

        internal void Raise(FeedbackCue cue) => this._events.Raise(HapticEventNames.For(cue));
    }
}
