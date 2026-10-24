using Godot;

namespace Nightwatch.Game.Ui.Controllers;

/// <summary>
/// 右侧精简大纲栏控制器（参照 israel_political_simulation AlertOutliner）：
/// 仅常驻「01 战前快速布防 + 开始守夜」「★ 保卫目标」「! 参谋建议与预警」三组高频摘要，
/// 底部提供 D2/D3/D6/D7 快捷菜单入口。
/// </summary>
public partial class AlertOutlinerController : PanelContainer
{
    [Signal]
    public delegate void StartNightPressedEventHandler();

    [Signal]
    public delegate void PresetSelectedEventHandler(string presetName);

    [Signal]
    public delegate void QuickDrawerRequestedEventHandler(int drawerIndex);

    private Label? _covVisibleLabel;
    private Label? _covBlindLabel;
    private Label? _advisorTextLabel;

    public override void _Ready()
    {
        _covVisibleLabel = GetNodeOrNull<Label>("VBox/DeployCard/CovGrid/VisBox/Val");
        _covBlindLabel = GetNodeOrNull<Label>("VBox/DeployCard/CovGrid/BlindBox/Val");
        _advisorTextLabel = GetNodeOrNull<Label>("VBox/AdvisorCard/AdvisorText");

        var btnStart = GetNodeOrNull<Button>("VBox/DeployCard/BtnStartNight");
        if (btnStart != null)
        {
            btnStart.Pressed += () => EmitSignal(SignalName.StartNightPressed);
        }

        BindPreset("VBox/DeployCard/PresetRow/BtnLayered", "layered");
        BindPreset("VBox/DeployCard/PresetRow/BtnDefault", "default");
        BindPreset("VBox/DeployCard/PresetRow/BtnStacked", "stacked");

        BindQuickDrawer("VBox/QuickMenuRow/BtnQuickD2", 2);
        BindQuickDrawer("VBox/QuickMenuRow/BtnQuickD3", 3);
        BindQuickDrawer("VBox/QuickMenuRow/BtnQuickD6", 6);
        BindQuickDrawer("VBox/QuickMenuRow/BtnQuickD7", 7);
    }

    public void UpdateCoverage(double visiblePct, double blindPct)
    {
        if (_covVisibleLabel != null)
        {
            _covVisibleLabel.Text = $"{visiblePct:F1}%";
        }
        if (_covBlindLabel != null)
        {
            _covBlindLabel.Text = $"{blindPct:F1}%";
        }
    }

    public void UpdateAdvisorMessage(string message)
    {
        if (_advisorTextLabel != null)
        {
            _advisorTextLabel.Text = message;
        }
    }

    private void BindPreset(string path, string presetName)
    {
        var btn = GetNodeOrNull<Button>(path);
        if (btn != null)
        {
            btn.Pressed += () => EmitSignal(SignalName.PresetSelected, presetName);
        }
    }

    private void BindQuickDrawer(string path, int drawerIndex)
    {
        var btn = GetNodeOrNull<Button>(path);
        if (btn != null)
        {
            btn.Pressed += () => EmitSignal(SignalName.QuickDrawerRequested, drawerIndex);
        }
    }
}
