#nullable enable

namespace Loupedeck.CodexActionRingPlugin.Logitech.Primary
{
    using Loupedeck.CodexActionRingPlugin.Core;

    public sealed class NextAttentionCommand : PrimaryActionCommand
    {
        public NextAttentionCommand()
            : base(RingActionId.NextAttention)
        {
        }

        internal NextAttentionCommand(IActionExecutor executor, IPrimaryFeedbackAdapter feedback)
            : base(RingActionId.NextAttention, executor, feedback)
        {
        }
    }

    public sealed class ViewActivityCommand : PrimaryActionCommand
    {
        public ViewActivityCommand()
            : base(RingActionId.ViewActivity)
        {
        }

        internal ViewActivityCommand(IActionExecutor executor, IPrimaryFeedbackAdapter feedback)
            : base(RingActionId.ViewActivity, executor, feedback)
        {
        }
    }

    public sealed class NewChatCommand : PrimaryActionCommand
    {
        public NewChatCommand()
            : base(RingActionId.NewChat)
        {
        }

        internal NewChatCommand(IActionExecutor executor, IPrimaryFeedbackAdapter feedback)
            : base(RingActionId.NewChat, executor, feedback)
        {
        }
    }

    public sealed class RecentlyViewedCommand : PrimaryActionCommand
    {
        public RecentlyViewedCommand()
            : base(RingActionId.RecentlyViewed)
        {
        }

        internal RecentlyViewedCommand(IActionExecutor executor, IPrimaryFeedbackAdapter feedback)
            : base(RingActionId.RecentlyViewed, executor, feedback)
        {
        }
    }

    public sealed class QuickChatCommand : PrimaryActionCommand
    {
        public QuickChatCommand()
            : base(RingActionId.QuickChat)
        {
        }

        internal QuickChatCommand(IActionExecutor executor, IPrimaryFeedbackAdapter feedback)
            : base(RingActionId.QuickChat, executor, feedback)
        {
        }
    }

    public sealed class DictationCommand : PrimaryActionCommand
    {
        public DictationCommand()
            : base(RingActionId.Dictation)
        {
        }

        internal DictationCommand(IActionExecutor executor, IPrimaryFeedbackAdapter feedback)
            : base(RingActionId.Dictation, executor, feedback)
        {
        }
    }

    public sealed class SideChatCommand : PrimaryActionCommand
    {
        public SideChatCommand()
            : base(RingActionId.SideChat)
        {
        }

        internal SideChatCommand(IActionExecutor executor, IPrimaryFeedbackAdapter feedback)
            : base(RingActionId.SideChat, executor, feedback)
        {
        }
    }

    public sealed class CopyDeepLinkCommand : PrimaryActionCommand
    {
        public CopyDeepLinkCommand()
            : base(RingActionId.CopyDeepLink)
        {
        }

        internal CopyDeepLinkCommand(IActionExecutor executor, IPrimaryFeedbackAdapter feedback)
            : base(RingActionId.CopyDeepLink, executor, feedback)
        {
        }
    }

    public sealed class SelectModelCommand : PrimaryActionCommand
    {
        public SelectModelCommand()
            : base(RingActionId.SelectModel)
        {
        }

        internal SelectModelCommand(IActionExecutor executor, IPrimaryFeedbackAdapter feedback)
            : base(RingActionId.SelectModel, executor, feedback)
        {
        }
    }
}
