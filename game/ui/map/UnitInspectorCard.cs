using Godot;

namespace Nightwatch.Game.Ui.Map;

/// <summary>
/// 浮动防空单位检查器卡片（参照 israel_political_simulation RegionInspectorCard）：
/// 点击地图或 D2 编制表上的单位时在左侧浮现，可随时点击右上角 × 收起以保持主地图清爽。
/// </summary>
public partial class UnitInspectorCard : PanelContainer
{
    [Signal]
    public delegate void EmissionPolicyChangedEventHandler(int rosterId, string policyId);

    [Signal]
    public delegate void FireDoctrineChangedEventHandler(int rosterId, string doctrineMode);

    private int _currentRosterId = 6;
    private Label? _titleLabel;
    private Label? _specLabel;
    private Label? _descLabel;
    private Label? _rangeLabel;
    private Label? _exposureLabel;
    private Button? _closeButton;

    public override void _Ready()
    {
        _titleLabel = GetNodeOrNull<Label>("VBox/HeaderRow/TitleLabel");
        _specLabel = GetNodeOrNull<Label>("VBox/WeaponBanner/SpecLabel");
        _descLabel = GetNodeOrNull<Label>("VBox/DescLabel");
        _rangeLabel = GetNodeOrNull<Label>("VBox/StatsRow/RangeVal");
        _exposureLabel = GetNodeOrNull<Label>("VBox/StatsRow/ExposureVal");
        _closeButton = GetNodeOrNull<Button>("VBox/HeaderRow/BtnClose");

        if (_closeButton != null)
        {
            _closeButton.Pressed += HideInspector;
        }

        BindPolicyButton("VBox/RadarRow/BtnContinuous", "continuous");
        BindPolicyButton("VBox/RadarRow/BtnBlink", "blink");
        BindPolicyButton("VBox/RadarRow/BtnSilent", "silent");

        BindDoctrineButton("VBox/DoctrineRow/BtnSave", "save");
        BindDoctrineButton("VBox/DoctrineRow/BtnAll", "all");
        BindDoctrineButton("VBox/DoctrineRow/BtnHold", "hold");
    }

    public void ShowUnit(int rosterId, string unitName, string specText, string descText, double rangeKm, int exposurePct)
    {
        _currentRosterId = rosterId;
        if (_titleLabel != null)
        {
            _titleLabel.Text = $"#{rosterId} {unitName}";
        }
        if (_specLabel != null)
        {
            _specLabel.Text = specText;
        }
        if (_descLabel != null)
        {
            _descLabel.Text = descText;
        }
        if (_rangeLabel != null)
        {
            _rangeLabel.Text = $"{rangeKm:F1} km";
        }
        if (_exposureLabel != null)
        {
            _exposureLabel.Text = $"{exposurePct}%";
        }
        Visible = true;
    }

    public void HideInspector()
    {
        Visible = false;
    }

    private void BindPolicyButton(string path, string policyId)
    {
        var btn = GetNodeOrNull<Button>(path);
        if (btn != null)
        {
            btn.Pressed += () => EmitSignal(SignalName.EmissionPolicyChanged, _currentRosterId, policyId);
        }
    }

    private void BindDoctrineButton(string path, string mode)
    {
        var btn = GetNodeOrNull<Button>(path);
        if (btn != null)
        {
            btn.Pressed += () => EmitSignal(SignalName.FireDoctrineChanged, _currentRosterId, mode);
        }
    }
}
