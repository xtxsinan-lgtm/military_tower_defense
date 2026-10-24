using Godot;
using Nightwatch.Game.Ui.Map;

namespace Nightwatch.Game.Ui.Controllers;

/// <summary>
/// 防空指挥所主工作台控制器（参照 israel_political_simulation DeskMainController）：
/// 统筹顶栏态势条（TopBar）、中央全幅战术地图（MapDeskLayer / TacticalMapCanvas）、
/// 浮动单位检查器（UnitInspectorCard）、按需展开的 D1–D7 部门抽屉（DrawerContainer）、
/// 底部 7 工位防空器械栏（DiegeticDeskPropsBar）与右侧精简大纲栏（AlertOutliner）。
/// </summary>
public partial class DeskMainController : Control
{
    [Signal]
    public delegate void DrawerRequestedEventHandler(int drawerIndex);

    [Signal]
    public delegate void StartNightRequestedEventHandler();

    [Signal]
    public delegate void PresetRequestedEventHandler(string presetName);

    [Export]
    public TopBarController? TopBar { get; set; }

    [Export]
    public TacticalMapCanvas? MapCanvas { get; set; }

    [Export]
    public UnitInspectorCard? UnitInspector { get; set; }

    [Export]
    public DrawerContainerController? DrawerContainer { get; set; }

    [Export]
    public DiegeticDeskPropsController? DeskPropsBar { get; set; }

    [Export]
    public AlertOutlinerController? AlertOutliner { get; set; }

    public int OpenDrawerIndex { get; private set; } = 0;

    public override void _Ready()
    {
        TopBar ??= GetNodeOrNull<TopBarController>("RootVBox/TopBar");
        MapCanvas ??= GetNodeOrNull<TacticalMapCanvas>("RootVBox/BodySplit/MapDeskLayer/CanvasWrapper/TacticalMapCanvas");
        UnitInspector ??= GetNodeOrNull<UnitInspectorCard>("RootVBox/BodySplit/MapDeskLayer/CanvasWrapper/UnitInspectorCard");
        DrawerContainer ??= GetNodeOrNull<DrawerContainerController>("RootVBox/BodySplit/MapDeskLayer/CanvasWrapper/DrawerContainer");
        DeskPropsBar ??= GetNodeOrNull<DiegeticDeskPropsController>("RootVBox/BodySplit/MapDeskLayer/DiegeticDeskPropsBar");
        AlertOutliner ??= GetNodeOrNull<AlertOutlinerController>("RootVBox/BodySplit/AlertOutliner");

        if (TopBar != null)
        {
            TopBar.KpiDrawerRequested += ToggleDrawer;
        }

        if (DeskPropsBar != null)
        {
            DeskPropsBar.PropActivated += ToggleDrawer;
        }

        if (DrawerContainer != null)
        {
            DrawerContainer.DrawerClosed += OnDrawerClosed;
        }

        if (AlertOutliner != null)
        {
            AlertOutliner.QuickDrawerRequested += ToggleDrawer;
            AlertOutliner.StartNightPressed += () => EmitSignal(SignalName.StartNightRequested);
            AlertOutliner.PresetSelected += (preset) => EmitSignal(SignalName.PresetRequested, preset);
        }

        if (MapCanvas != null)
        {
            MapCanvas.UnitSelected += OnMapUnitSelected;
        }

        // 绑定地图工具条上的 D1–D7 顶部快捷页签按钮
        BindToolbarDrawerTabs();
        BindToolbarZoomButtons();
    }

    public override void _UnhandledKeyInput(InputEvent @event)
    {
        if (@event is not InputEventKey keyEvent || !keyEvent.Pressed || keyEvent.Echo)
        {
            return;
        }

        if (keyEvent.Keycode >= Key.F1 && keyEvent.Keycode <= Key.F7)
        {
            int idx = (int)(keyEvent.Keycode - Key.F1) + 1;
            ToggleDrawer(idx);
            GetViewport().SetInputAsHandled();
            return;
        }

        if (keyEvent.Keycode == Key.Escape)
        {
            if (OpenDrawerIndex != 0)
            {
                CloseDrawer();
                GetViewport().SetInputAsHandled();
            }
            else if (UnitInspector != null && UnitInspector.Visible)
            {
                UnitInspector.HideInspector();
                GetViewport().SetInputAsHandled();
            }
        }
    }

    public void OpenDrawer(int drawerIndex)
    {
        int clamped = Mathf.Clamp(drawerIndex, 0, 7);
        if (clamped == 0)
        {
            CloseDrawer();
            return;
        }

        OpenDrawerIndex = clamped;
        DrawerContainer?.OpenDrawer(clamped);
        DeskPropsBar?.SetActiveDrawer(clamped);
        TopBar?.SetActiveDrawer(clamped);
        SyncToolbarTabHighlight(clamped);

        // 打开抽屉时自动收起左侧浮动单位检查器，避免画面拥挤
        if (UnitInspector != null)
        {
            UnitInspector.Visible = false;
        }

        EmitSignal(SignalName.DrawerRequested, clamped);
    }

    public void CloseDrawer()
    {
        OpenDrawerIndex = 0;
        DrawerContainer?.CloseAll();
        DeskPropsBar?.SetActiveDrawer(0);
        TopBar?.SetActiveDrawer(0);
        SyncToolbarTabHighlight(0);
    }

    public void ToggleDrawer(int drawerIndex)
    {
        if (OpenDrawerIndex == drawerIndex)
        {
            CloseDrawer();
        }
        else
        {
            OpenDrawer(drawerIndex);
        }
    }

    private void OnDrawerClosed()
    {
        OpenDrawerIndex = 0;
        DeskPropsBar?.SetActiveDrawer(0);
        TopBar?.SetActiveDrawer(0);
        SyncToolbarTabHighlight(0);
    }

    private void OnMapUnitSelected(int rosterId, string unitName, string specText, string descText, double rangeKm, int exposurePct)
    {
        if (OpenDrawerIndex != 0)
        {
            CloseDrawer();
        }

        UnitInspector?.ShowUnit(rosterId, unitName, specText, descText, rangeKm, exposurePct);
    }

    private void BindToolbarDrawerTabs()
    {
        var tabRow = GetNodeOrNull<HBoxContainer>("RootVBox/BodySplit/MapDeskLayer/MapToolbar/DrawerTabs");
        if (tabRow == null)
        {
            return;
        }

        for (int i = 1; i <= 7; i++)
        {
            int idx = i;
            var btn = tabRow.GetNodeOrNull<Button>($"BtnD{idx}");
            if (btn != null)
            {
                btn.Pressed += () => ToggleDrawer(idx);
            }
        }
    }

    private void SyncToolbarTabHighlight(int activeIndex)
    {
        var tabRow = GetNodeOrNull<HBoxContainer>("RootVBox/BodySplit/MapDeskLayer/MapToolbar/DrawerTabs");
        if (tabRow == null)
        {
            return;
        }

        for (int i = 1; i <= 7; i++)
        {
            var btn = tabRow.GetNodeOrNull<Button>($"BtnD{i}");
            if (btn != null)
            {
                btn.ButtonPressed = (i == activeIndex);
            }
        }
    }

    private void BindToolbarZoomButtons()
    {
        var btnOut = GetNodeOrNull<Button>("RootVBox/BodySplit/MapDeskLayer/MapToolbar/RightTools/BtnZoomOut");
        var btnReset = GetNodeOrNull<Button>("RootVBox/BodySplit/MapDeskLayer/MapToolbar/RightTools/BtnZoomReset");
        var btnIn = GetNodeOrNull<Button>("RootVBox/BodySplit/MapDeskLayer/MapToolbar/RightTools/BtnZoomIn");

        if (btnOut != null)
        {
            btnOut.Pressed += () => MapCanvas?.StepZoom(1.0 / 1.25);
        }
        if (btnReset != null)
        {
            btnReset.Pressed += () => MapCanvas?.ResetCamera();
        }
        if (btnIn != null)
        {
            btnIn.Pressed += () => MapCanvas?.StepZoom(1.25);
        }

        if (MapCanvas != null && btnReset != null)
        {
            MapCanvas.ZoomChanged += (zoomFactor) =>
            {
                btnReset.Text = $"{Mathf.RoundToInt((float)(zoomFactor * 100.0))}%";
            };
        }
    }
}
