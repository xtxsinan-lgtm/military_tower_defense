using Godot;
using Nightwatch.Game.Ui.Controllers;

namespace Nightwatch.Game.App;

/// <summary>
/// 《守夜》Nightwatch Godot 4 主入口节点。
/// 负责初始化输入映射、加载防空指挥所主工作台（DeskMain）并驱动阶段状态机。
/// </summary>
public partial class Main : Control
{
    [Export]
    public DeskMainController? DeskMain { get; set; }

    public override void _Ready()
    {
        // 设置深色指挥所清屏底色 (#0b0f14)
        RenderingServer.SetDefaultClearColor(Color.FromHtml("#0b0f14"));
        InputSetup.EnsureActions();

        DeskMain ??= GetNodeOrNull<DeskMainController>("DeskMain");
    }
}
