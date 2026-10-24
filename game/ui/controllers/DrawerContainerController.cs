using Godot;

namespace Nightwatch.Game.Ui.Controllers;

/// <summary>
/// D1–D7 指挥所部门抽屉容器控制器（参照 israel_political_simulation DrawerContainerController）：
/// 管理 7 个部门抽屉面板的按需切换、标题更新与关闭动作。
/// </summary>
public partial class DrawerContainerController : PanelContainer
{
    [Signal]
    public delegate void DrawerClosedEventHandler();

    private Label? _codeBadge;
    private Label? _titleLabel;
    private Button? _closeButton;
    private readonly Control?[] _slots = new Control?[7];

    private static readonly (string Code, string Title)[] DrawerMeta =
    {
        ("D1", "战前部署与阵型沙盘"),
        ("D2", "防空武器与雷达编制"),
        ("D3", "火控纪律与电磁条令"),
        ("D4", "空袭情报与来袭走廊"),
        ("D5", "城市电网与保卫目标"),
        ("D6", "导弹库存与战备补给"),
        ("D7", "值班作战室与战况日志"),
    };

    public int ActiveDrawerIndex { get; private set; } = 0;

    public override void _Ready()
    {
        _codeBadge = GetNodeOrNull<Label>("VBox/HeaderBar/TitleRow/CodeBadge");
        _titleLabel = GetNodeOrNull<Label>("VBox/HeaderBar/TitleRow/TitleLabel");
        _closeButton = GetNodeOrNull<Button>("VBox/HeaderBar/CloseButton");

        if (_closeButton != null)
        {
            _closeButton.Pressed += () =>
            {
                CloseAll();
                EmitSignal(SignalName.DrawerClosed);
            };
        }

        for (int i = 1; i <= 7; i++)
        {
            _slots[i - 1] = GetNodeOrNull<Control>($"VBox/BodyScroll/SlotContainer/SlotD{i}");
        }

        Visible = false;
    }

    public void OpenDrawer(int drawerIndex)
    {
        if (drawerIndex < 1 || drawerIndex > 7)
        {
            CloseAll();
            return;
        }

        ActiveDrawerIndex = drawerIndex;
        var meta = DrawerMeta[drawerIndex - 1];
        if (_codeBadge != null)
        {
            _codeBadge.Text = meta.Code;
        }
        if (_titleLabel != null)
        {
            _titleLabel.Text = meta.Title;
        }

        for (int i = 0; i < _slots.Length; i++)
        {
            if (_slots[i] != null)
            {
                _slots[i]!.Visible = (i + 1 == drawerIndex);
            }
        }

        Visible = true;
    }

    public void CloseAll()
    {
        ActiveDrawerIndex = 0;
        Visible = false;
    }
}
