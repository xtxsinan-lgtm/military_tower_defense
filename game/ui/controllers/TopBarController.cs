using Godot;

namespace Nightwatch.Game.Ui.Controllers;

/// <summary>
/// 顶栏态势与时间控制器（参照 israel_political_simulation TopBar）：
/// 包含任务标识、5 个可点击态势指标槽（点击直达 D1/D2/D3/D6/D5 抽屉）、世界时钟与倍速控制。
/// </summary>
public partial class TopBarController : PanelContainer
{
    [Signal]
    public delegate void KpiDrawerRequestedEventHandler(int drawerIndex);

    [Signal]
    public delegate void SpeedSelectedEventHandler(double speedMultiplier);

    [Signal]
    public delegate void SkipWaveRequestedEventHandler();

    private Label? _covValueLabel;
    private Label? _rosterValueLabel;
    private Label? _cpValueLabel;
    private Label? _trustValueLabel;
    private Label? _structValueLabel;
    private Label? _clockDigitsLabel;
    private Label? _clockSubLabel;
    private ProgressBar? _clockProgress;

    private readonly Button?[] _slotButtons = new Button?[5];
    private static readonly int[] SlotDrawerMap = { 1, 2, 3, 6, 5 };

    public override void _Ready()
    {
        _covValueLabel = GetNodeOrNull<Label>("HBox/KpiStrip/SlotCoverage/VBox/ValueLabel");
        _rosterValueLabel = GetNodeOrNull<Label>("HBox/KpiStrip/SlotRoster/VBox/ValueLabel");
        _cpValueLabel = GetNodeOrNull<Label>("HBox/KpiStrip/SlotCp/VBox/ValueLabel");
        _trustValueLabel = GetNodeOrNull<Label>("HBox/KpiStrip/SlotTrust/VBox/ValueLabel");
        _structValueLabel = GetNodeOrNull<Label>("HBox/KpiStrip/SlotStruct/VBox/ValueLabel");

        _clockDigitsLabel = GetNodeOrNull<Label>("HBox/ClockBox/ReadoutRow/ClockDigits");
        _clockSubLabel = GetNodeOrNull<Label>("HBox/ClockBox/ReadoutRow/ClockSub");
        _clockProgress = GetNodeOrNull<ProgressBar>("HBox/ClockBox/ClockProgress");

        string[] slotNames = { "SlotCoverage", "SlotRoster", "SlotCp", "SlotTrust", "SlotStruct" };
        for (int i = 0; i < slotNames.Length; i++)
        {
            int drawerIdx = SlotDrawerMap[i];
            var btn = GetNodeOrNull<Button>($"HBox/KpiStrip/{slotNames[i]}");
            _slotButtons[i] = btn;
            if (btn != null)
            {
                btn.Pressed += () => EmitSignal(SignalName.KpiDrawerRequested, drawerIdx);
            }
        }

        BindSpeedButton("HBox/SpeedControls/BtnPause", 0.0);
        BindSpeedButton("HBox/SpeedControls/BtnSpeed1", 1.0);
        BindSpeedButton("HBox/SpeedControls/BtnSpeed4", 4.0);
        BindSpeedButton("HBox/SpeedControls/BtnSpeed8", 8.0);

        var btnSkip = GetNodeOrNull<Button>("HBox/SpeedControls/BtnSkip");
        if (btnSkip != null)
        {
            btnSkip.Pressed += () => EmitSignal(SignalName.SkipWaveRequested);
        }
    }

    public void UpdateKpis(double visibleFrac, double blindFrac, int fireCount, int radarCount, int cpCur, int cpMax, double trust, int structOk, int structTotal)
    {
        if (_covValueLabel != null)
        {
            _covValueLabel.Text = $"{visibleFrac * 100.0:F1}% / {blindFrac * 100.0:F1}%";
        }
        if (_rosterValueLabel != null)
        {
            _rosterValueLabel.Text = $"{fireCount}火力·{radarCount}雷达";
        }
        if (_cpValueLabel != null)
        {
            _cpValueLabel.Text = $"{cpCur} / {cpMax}";
        }
        if (_trustValueLabel != null)
        {
            _trustValueLabel.Text = $"{trust:F1}";
        }
        if (_structValueLabel != null)
        {
            _structValueLabel.Text = $"{structOk}/{structTotal} 完好";
        }
    }

    public void UpdateClock(string timeText, string subText, double progressRatio)
    {
        if (_clockDigitsLabel != null)
        {
            _clockDigitsLabel.Text = timeText;
        }
        if (_clockSubLabel != null)
        {
            _clockSubLabel.Text = subText;
        }
        if (_clockProgress != null)
        {
            _clockProgress.Value = Mathf.Clamp(progressRatio * 100.0, 0.0, 100.0);
        }
    }

    public void SetActiveDrawer(int drawerIndex)
    {
        for (int i = 0; i < _slotButtons.Length; i++)
        {
            var btn = _slotButtons[i];
            if (btn != null)
            {
                btn.ButtonPressed = (SlotDrawerMap[i] == drawerIndex);
            }
        }
    }

    private void BindSpeedButton(string nodePath, double speed)
    {
        var btn = GetNodeOrNull<Button>(nodePath);
        if (btn != null)
        {
            btn.Pressed += () => EmitSignal(SignalName.SpeedSelected, speed);
        }
    }
}
