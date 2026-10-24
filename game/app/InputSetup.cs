using Godot;

namespace Nightwatch.Game.App;

/// <summary>
/// 启动时注册 Godot 4 输入动作（含相机平移、缩放、时间控制与 D1–D7 指挥所抽屉快捷键）。
/// 遵循 docs/spec/06_client_graybox.md §2.2 与 §2.6：不在 project.godot 中手写序列化 InputEvent。
/// </summary>
public static class InputSetup
{
    public static void EnsureActions()
    {
        AddKeyAction("cam_pan_up", Key.W, Key.Up);
        AddKeyAction("cam_pan_down", Key.S, Key.Down);
        AddKeyAction("cam_pan_left", Key.A, Key.Left);
        AddKeyAction("cam_pan_right", Key.D, Key.Right);
        AddKeyAction("cam_reset_fit", Key.Home, Key.Key0);

        AddKeyAction("time_toggle_pause", Key.Space);
        AddKeyAction("time_speed_1", Key.Key1);
        AddKeyAction("time_speed_2", Key.Key2);
        AddKeyAction("time_speed_3", Key.Key3);
        AddKeyAction("time_skip_wave", Key.N);

        // D1–D7 指挥所部门菜单抽屉快捷键（参照 israel_political_simulation 多菜单工作台）
        AddKeyAction("desk_drawer_1", Key.F1);
        AddKeyAction("desk_drawer_2", Key.F2);
        AddKeyAction("desk_drawer_3", Key.F3);
        AddKeyAction("desk_drawer_4", Key.F4);
        AddKeyAction("desk_drawer_5", Key.F5);
        AddKeyAction("desk_drawer_6", Key.F6);
        AddKeyAction("desk_drawer_7", Key.F7);
        AddKeyAction("desk_close_modal", Key.Escape);

        AddKeyAction("debug_toggle", Key.F12, Key.Quoteleft);
    }

    private static void AddKeyAction(string actionName, params Key[] keys)
    {
        if (!InputMap.HasAction(actionName))
        {
            InputMap.AddAction(actionName);
        }

        foreach (Key k in keys)
        {
            var ev = new InputEventKey { PhysicalKeycode = k, Keycode = k };
            if (!InputMap.ActionHasEvent(actionName, ev))
            {
                InputMap.ActionAddEvent(actionName, ev);
            }
        }
    }
}
