using Godot;

namespace Nightwatch.Game.Ui.Controllers;

/// <summary>
/// 底部 7 工位防空指挥所器械菜单栏控制器（参照 israel_political_simulation DiegeticDeskPropsController）：
/// 将沙盘标图板 (D1)、防空编制簿 (D2)、火控控制台 (D3)、预警电传机 (D4)、
/// 电网监控屏 (D5)、弹药军械库 (D6)、值班作战室 (D7) 映射到按需抽屉。
/// </summary>
public partial class DiegeticDeskPropsController : PanelContainer
{
    [Signal]
    public delegate void PropActivatedEventHandler(int drawerIndex);

    private readonly Button?[] _propButtons = new Button?[7];

    public override void _Ready()
    {
        for (int i = 1; i <= 7; i++)
        {
            int drawerIdx = i;
            var btn = GetNodeOrNull<Button>($"PropsGrid/PropD{drawerIdx}");
            _propButtons[i - 1] = btn;
            if (btn != null)
            {
                btn.Pressed += () => EmitSignal(SignalName.PropActivated, drawerIdx);
            }
        }
    }

    public void SetActiveDrawer(int drawerIndex)
    {
        for (int i = 0; i < _propButtons.Length; i++)
        {
            var btn = _propButtons[i];
            if (btn != null)
            {
                btn.ButtonPressed = (i + 1 == drawerIndex);
            }
        }
    }
}
