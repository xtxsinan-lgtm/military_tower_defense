using Godot;
using Nightwatch.Game.Ui.Map;

namespace Nightwatch.Game.Ui.Controllers;

/// <summary>
/// 防空指挥所主工作台控制器（参照 israel_political_simulation DeskMainController）：
/// 统筹顶栏态势条（TopBar）、中央全幅战术地图（MapDeskLayer / TacticalMapCanvas）、
/// 浮动单位检查器（UnitInspectorCard）、按需展开的 D1–D7 部门抽屉（DrawerContainer）、
/// 底部 7 工位防空器械栏（DiegeticDeskPropsBar）与右侧精简大纲栏（AlertOutliner）。
/// 布局为 DEFCON 式“全屏地图 + 浮动 HUD”：MapLayer 铺满窗口，HudLayer 中各浮层锚定在屏幕四角 / 四边；
/// 本控制器负责把浮层占用的四边留白（安全区）同步给地图，使作战区始终在可见区域内居中。
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
        TopBar ??= GetNodeOrNull<TopBarController>("HudLayer/TopBar");
        MapCanvas ??= GetNodeOrNull<TacticalMapCanvas>("MapLayer/TacticalMapCanvas");
        UnitInspector ??= GetNodeOrNull<UnitInspectorCard>("HudLayer/UnitInspectorCard");
        DrawerContainer ??= GetNodeOrNull<DrawerContainerController>("HudLayer/DrawerContainer");
        DeskPropsBar ??= GetNodeOrNull<DiegeticDeskPropsController>("HudLayer/BottomDock/DiegeticDeskPropsBar");
        AlertOutliner ??= GetNodeOrNull<AlertOutlinerController>("HudLayer/AlertOutliner");

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

        // HUD 浮层尺寸或显隐变化时，重新计算地图安全区
        Resized += QueueSafeAreaUpdate;
        foreach (Control? hud in new Control?[] { TopBar, AlertOutliner, DeskPropsBar })
        {
            if (hud != null)
            {
                hud.Resized += QueueSafeAreaUpdate;
                hud.VisibilityChanged += QueueSafeAreaUpdate;
            }
        }
        QueueSafeAreaUpdate();
    }

    private void QueueSafeAreaUpdate()
    {
        Callable.From(UpdateMapSafeArea).CallDeferred();
    }

    /// <summary>
    /// 计算 HUD 浮层占用的四边留白：上 = 顶部态势条底边，右 = 作战面板左缘，下 = 底部指挥台顶边。
    /// 左侧检查器 / 抽屉是按需浮出的上下文浮窗，不计入安全区（与网页原型一致）。
    /// </summary>
    private void UpdateMapSafeArea()
    {
        if (MapCanvas == null)
        {
            return;
        }

        Rect2 root = GetGlobalRect();
        const float pad = 6.0f;
        float top = pad, right = pad, bottom = pad, left = pad;
        if (TopBar != null && TopBar.Visible)
        {
            top = TopBar.GetGlobalRect().End.Y - root.Position.Y + pad;
        }
        if (AlertOutliner != null && AlertOutliner.Visible)
        {
            right = root.End.X - AlertOutliner.GetGlobalRect().Position.X + pad;
        }
        if (DeskPropsBar != null && DeskPropsBar.Visible)
        {
            bottom = root.End.Y - DeskPropsBar.GetGlobalRect().Position.Y + pad;
        }
        MapCanvas.SetSafeMargins(new Vector4(left, top, right, bottom));
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
    }

    private void OnMapUnitSelected(int rosterId, string unitName, string specText, string descText, double rangeKm, int exposurePct)
    {
        if (OpenDrawerIndex != 0)
        {
            CloseDrawer();
        }

        UnitInspector?.ShowUnit(rosterId, unitName, specText, descText, rangeKm, exposurePct);
    }
}
