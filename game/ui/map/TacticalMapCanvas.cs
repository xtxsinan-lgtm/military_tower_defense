using System;
using System.Collections.Generic;
using Godot;

namespace Nightwatch.Game.Ui.Map;

/// <summary>
/// 战术防空标绘地图画布（Godot 4 Control）：
/// 支持鼠标滚轮以光标为中心缩放、中键/右键拖拽平移、iPad / 触控屏双指捏合缩放（InputEventMagnifyGesture 与多点触控），
/// 并以北约军标风格矢量绘制保卫目标、山脊盲区、防空火力与射程圈。
/// 画布铺满整个窗口（DEFCON 式全屏地图）：HUD 浮层占用的四边留白通过 <see cref="SetSafeMargins"/> 传入，
/// 作战区正方形在安全区内居中；安全区之外继续绘制区外参考网格，地图不再被面板挤成小方块。
/// </summary>
public partial class TacticalMapCanvas : Control
{
    [Signal]
    public delegate void ZoomChangedEventHandler(double zoomFactor);

    [Signal]
    public delegate void UnitSelectedEventHandler(int rosterId, string unitName, string specText, string descText, double rangeKm, int exposurePct);

    public sealed class MapUnitMarker
    {
        public int RosterId { get; init; }
        public string UnitDefId { get; init; } = "";
        public string Name { get; init; } = "";
        public string SpecText { get; init; } = "";
        public string DescText { get; init; } = "";
        public Vector2 NormalizedPos { get; set; }
        public double RangeKm { get; init; }
        public int ExposurePct { get; set; }
        public bool IsSensor { get; init; }
    }

    public sealed class ProtectedStructureMarker
    {
        public string Id { get; init; } = "";
        public string Name { get; init; } = "";
        public Vector2 NormalizedPos { get; init; }
        public int Hp { get; set; }
        public int MaxHp { get; init; }
    }

    private double _zoom = 1.0;
    private Vector2 _panOffsetPx = Vector2.Zero;
    // HUD 浮层占用的四边留白（像素）：X = 左，Y = 上，Z = 右，W = 下
    private Vector4 _safeMargins = Vector4.Zero;
    private bool _isPanning;
    private Vector2 _panStartMouse;
    private Vector2 _panStartOffset;
    private MapUnitMarker? _draggingUnit;
    private int _selectedRosterId = 6;

    // iPad / 触控屏双指捏合状态表（按手指 index 升序计算，保证确定性）
    private readonly SortedDictionary<int, Vector2> _activeTouches = new();
    private float _pinchInitialDist;
    private double _pinchInitialZoom = 1.0;
    private Vector2 _pinchInitialPan = Vector2.Zero;
    private Vector2 _pinchInitialMid = Vector2.Zero;

    private readonly List<ProtectedStructureMarker> _structures = new()
    {
        new ProtectedStructureMarker { Id = "power_plant", Name = "★ 核心保卫·热电厂", NormalizedPos = new Vector2(0.58f, 0.62f), Hp = 20, MaxHp = 20 },
        new ProtectedStructureMarker { Id = "substation", Name = "★ 保卫·中心变电站", NormalizedPos = new Vector2(0.49f, 0.51f), Hp = 15, MaxHp = 15 },
        new ProtectedStructureMarker { Id = "water_plant", Name = "★ 保卫·水厂", NormalizedPos = new Vector2(0.39f, 0.44f), Hp = 12, MaxHp = 12 },
    };

    private readonly List<MapUnitMarker> _units = new()
    {
        new MapUnitMarker
        {
            RosterId = 6, UnitDefId = "nasams", Name = "NASAMS 中程防空导弹",
            SpecText = "AIM-120 中程防空导弹（25 km）+ 火控雷达",
            DescText = "全城防空网核心主力，射程覆盖大半个战区。自带火控雷达，注意用闪烁/静默控制暴露度。",
            NormalizedPos = new Vector2(0.46f, 0.56f), RangeKm = 25.0, ExposurePct = 0
        },
        new MapUnitMarker
        {
            RosterId = 5, UnitDefId = "iris_t_sls", Name = "IRIS-T 近程导弹车",
            SpecText = "IRIS-T 红外近程防空导弹（12 km）",
            DescText = "光电红外被动制导，零电磁暴露。建议设为“只打导弹”，专拦西北低空巡航导弹。",
            NormalizedPos = new Vector2(0.55f, 0.52f), RangeKm = 12.0, ExposurePct = 0
        },
        new MapUnitMarker
        {
            RosterId = 1, UnitDefId = "mobile_fire_team", Name = "皮卡高射机枪组",
            SpecText = "双联 12.7mm 高射机枪 + 探照灯",
            DescText = "无限弹链，前推东路走廊专门扫射廉价自杀式无人机群，替防空导弹省弹药。",
            NormalizedPos = new Vector2(0.64f, 0.45f), RangeKm = 1.8, ExposurePct = 0
        },
        new MapUnitMarker
        {
            RosterId = 2, UnitDefId = "mobile_fire_team", Name = "皮卡高射机枪组",
            SpecText = "双联 12.7mm 高射机枪 + 探照灯",
            DescText = "无限弹链，前推东路走廊专门扫射廉价自杀式无人机群，替防空导弹省弹药。",
            NormalizedPos = new Vector2(0.66f, 0.49f), RangeKm = 1.8, ExposurePct = 0
        },
        new MapUnitMarker
        {
            RosterId = 3, UnitDefId = "mobile_fire_team", Name = "皮卡高射机枪组",
            SpecText = "双联 12.7mm 高射机枪 + 探照灯",
            DescText = "无限弹链，前推东路走廊专门扫射廉价自杀式无人机群，替防空导弹省弹药。",
            NormalizedPos = new Vector2(0.63f, 0.54f), RangeKm = 1.8, ExposurePct = 0
        },
        new MapUnitMarker
        {
            RosterId = 4, UnitDefId = "mobile_fire_team", Name = "皮卡高射机枪组",
            SpecText = "双联 12.7mm 高射机枪 + 探照灯",
            DescText = "无限弹链，布置于热电厂外围近防拦截漏网无人机。",
            NormalizedPos = new Vector2(0.60f, 0.57f), RangeKm = 1.8, ExposurePct = 0
        },
        new MapUnitMarker
        {
            RosterId = 7, UnitDefId = "soviet_mid_range_radar", Name = "苏制警戒雷达站",
            SpecText = "150 km 区域搜索雷达（无武装）",
            DescText = "远距离发现敌机并替全场防空武器指示目标。北山脊会挡住它看低空。",
            NormalizedPos = new Vector2(0.53f, 0.54f), RangeKm = 45.0, ExposurePct = 0, IsSensor = true
        },
    };

    public override void _Ready()
    {
        ClipContents = true;
        MouseFilter = MouseFilterEnum.Stop;

        var zoomInBtn = GetNodeOrNull<Button>("ZoomDock/VBox/BtnDockZoomIn");
        var zoomResetBtn = GetNodeOrNull<Button>("ZoomDock/VBox/BtnDockZoomReset");
        var zoomOutBtn = GetNodeOrNull<Button>("ZoomDock/VBox/BtnDockZoomOut");

        if (zoomInBtn != null)
        {
            zoomInBtn.Pressed += () => StepZoom(1.25);
        }
        if (zoomResetBtn != null)
        {
            zoomResetBtn.Pressed += ResetCamera;
        }
        if (zoomOutBtn != null)
        {
            zoomOutBtn.Pressed += () => StepZoom(1.0 / 1.25);
        }
    }

    public void StepZoom(double factor)
    {
        ZoomAt(_zoom * factor, SafeCenter());
    }

    /// <summary>设置 HUD 安全区留白（左、上、右、下，像素），作战区随之在剩余区域内居中。</summary>
    public void SetSafeMargins(Vector4 margins)
    {
        if (margins.IsEqualApprox(_safeMargins))
        {
            return;
        }
        _safeMargins = margins;
        ClampPan();
        QueueRedraw();
    }

    private Vector2 SafeCenter()
    {
        float w = Math.Max(1.0f, Size.X - _safeMargins.X - _safeMargins.Z);
        float h = Math.Max(1.0f, Size.Y - _safeMargins.Y - _safeMargins.W);
        return new Vector2(_safeMargins.X + w * 0.5f, _safeMargins.Y + h * 0.5f);
    }

    private float BaseSide()
    {
        float w = Size.X - _safeMargins.X - _safeMargins.Z;
        float h = Size.Y - _safeMargins.Y - _safeMargins.W;
        return Math.Max(120.0f, Math.Min(w, h)) * 0.94f;
    }

    private Rect2 CurrentMapRect()
    {
        float side = BaseSide() * (float)_zoom;
        Vector2 origin = SafeCenter() + _panOffsetPx - new Vector2(side * 0.5f, side * 0.5f);
        return new Rect2(origin, new Vector2(side, side));
    }

    public void ResetCamera()
    {
        _zoom = 1.0;
        _panOffsetPx = Vector2.Zero;
        UpdateDockLabel();
        EmitSignal(SignalName.ZoomChanged, _zoom);
        QueueRedraw();
    }

    public void ZoomAt(double targetZoom, Vector2 anchorLocalPx)
    {
        double nextZoom = Math.Clamp(targetZoom, 0.65, 4.0);
        Vector2 center = SafeCenter();
        Vector2 worldBefore = (anchorLocalPx - center - _panOffsetPx) / (float)_zoom;
        _zoom = nextZoom;
        _panOffsetPx = anchorLocalPx - center - worldBefore * (float)_zoom;
        ClampPan();
        UpdateDockLabel();
        EmitSignal(SignalName.ZoomChanged, _zoom);
        QueueRedraw();
    }

    public override void _GuiInput(InputEvent @event)
    {
        // 1. macOS 触控板 / iPad 捏合手势
        if (@event is InputEventMagnifyGesture magnify)
        {
            ZoomAt(_zoom * magnify.Factor, magnify.Position);
            AcceptEvent();
            return;
        }

        if (@event is InputEventPanGesture panGesture)
        {
            _panOffsetPx -= panGesture.Delta * 12.0f;
            ClampPan();
            QueueRedraw();
            AcceptEvent();
            return;
        }

        // 2. iPad / 触控屏双指捏合缩放与拖拽平移
        if (@event is InputEventScreenTouch touchEvent)
        {
            if (touchEvent.Pressed)
            {
                _activeTouches[touchEvent.Index] = touchEvent.Position;
            }
            else
            {
                _activeTouches.Remove(touchEvent.Index);
            }

            if (_activeTouches.Count == 2)
            {
                var pts = new List<Vector2>(_activeTouches.Values);
                float dx = pts[0].X - pts[1].X;
                float dy = pts[0].Y - pts[1].Y;
                _pinchInitialDist = (float)Math.Sqrt(dx * dx + dy * dy);
                _pinchInitialZoom = _zoom;
                _pinchInitialPan = _panOffsetPx;
                _pinchInitialMid = (pts[0] + pts[1]) * 0.5f;
            }
            AcceptEvent();
            return;
        }

        if (@event is InputEventScreenDrag dragEvent)
        {
            _activeTouches[dragEvent.Index] = dragEvent.Position;
            if (_activeTouches.Count >= 2)
            {
                var pts = new List<Vector2>(_activeTouches.Values);
                float dx = pts[0].X - pts[1].X;
                float dy = pts[0].Y - pts[1].Y;
                float curDist = (float)Math.Sqrt(dx * dx + dy * dy);
                Vector2 curMid = (pts[0] + pts[1]) * 0.5f;
                if (_pinchInitialDist > 8.0f)
                {
                    double ratio = curDist / _pinchInitialDist;
                    double nextZ = Math.Clamp(_pinchInitialZoom * ratio, 0.65, 4.0);
                    Vector2 center = SafeCenter();
                    Vector2 worldAnchor = (_pinchInitialMid - center - _pinchInitialPan) / (float)_pinchInitialZoom;
                    _zoom = nextZ;
                    _panOffsetPx = curMid - center - worldAnchor * (float)_zoom;
                    ClampPan();
                    UpdateDockLabel();
                    EmitSignal(SignalName.ZoomChanged, _zoom);
                    QueueRedraw();
                }
                AcceptEvent();
                return;
            }
        }

        // 3. 鼠标滚轮缩放与单位拾取 / 平移
        if (@event is InputEventMouseButton mb)
        {
            if (mb.Pressed && mb.ButtonIndex == MouseButton.WheelUp)
            {
                ZoomAt(_zoom * 1.15, mb.Position);
                AcceptEvent();
                return;
            }
            if (mb.Pressed && mb.ButtonIndex == MouseButton.WheelDown)
            {
                ZoomAt(_zoom / 1.15, mb.Position);
                AcceptEvent();
                return;
            }

            if (mb.ButtonIndex == MouseButton.Left)
            {
                if (mb.Pressed)
                {
                    var picked = PickUnit(mb.Position, 20.0f);
                    if (picked != null)
                    {
                        _selectedRosterId = picked.RosterId;
                        _draggingUnit = picked;
                        EmitSignal(
                            SignalName.UnitSelected,
                            picked.RosterId,
                            picked.Name,
                            picked.SpecText,
                            picked.DescText,
                            picked.RangeKm,
                            picked.ExposurePct
                        );
                        QueueRedraw();
                    }
                    else
                    {
                        _isPanning = true;
                        _panStartMouse = mb.Position;
                        _panStartOffset = _panOffsetPx;
                    }
                }
                else
                {
                    _draggingUnit = null;
                    _isPanning = false;
                }
                AcceptEvent();
                return;
            }

            if (mb.ButtonIndex == MouseButton.Right || mb.ButtonIndex == MouseButton.Middle)
            {
                _isPanning = mb.Pressed;
                _panStartMouse = mb.Position;
                _panStartOffset = _panOffsetPx;
                AcceptEvent();
            }
        }

        if (@event is InputEventMouseMotion mm)
        {
            if (_draggingUnit != null)
            {
                Vector2 norm = ScreenToNormalized(mm.Position);
                _draggingUnit.NormalizedPos = new Vector2(
                    Mathf.Clamp(norm.X, 0.08f, 0.92f),
                    Mathf.Clamp(norm.Y, 0.08f, 0.92f)
                );
                QueueRedraw();
                AcceptEvent();
            }
            else if (_isPanning)
            {
                _panOffsetPx = _panStartOffset + (mm.Position - _panStartMouse);
                ClampPan();
                QueueRedraw();
                AcceptEvent();
            }
        }
    }

    public override void _Draw()
    {
        Rect2 rect = new Rect2(Vector2.Zero, Size);
        DrawRect(rect, Color.FromHtml("#070a0e"), true);

        Rect2 mapRect = CurrentMapRect();
        float side = mapRect.Size.X;

        // 0. 区外参考网格：与作战区 8×8 方格对齐并延伸到整个窗口（全屏“标图桌”）
        float cell = side / 8.0f;
        if (cell > 4.0f)
        {
            Color outerGrid = new Color(0.47f, 0.59f, 0.71f, 0.06f);
            float startX = mapRect.Position.X - Mathf.Ceil(mapRect.Position.X / cell) * cell;
            for (float x = startX; x <= Size.X; x += cell)
            {
                DrawLine(new Vector2(x, 0), new Vector2(x, Size.Y), outerGrid, 1.0f);
            }
            float startY = mapRect.Position.Y - Mathf.Ceil(mapRect.Position.Y / cell) * cell;
            for (float y = startY; y <= Size.Y; y += cell)
            {
                DrawLine(new Vector2(0, y), new Vector2(Size.X, y), outerGrid, 1.0f);
            }
        }

        DrawRect(mapRect, Color.FromHtml("#0b1118"), true);
        DrawRect(mapRect, Color.FromHtml("#223244"), false, 1.5f);

        // 1. 8x8 战术坐标网格
        Color gridColor = new Color(0.37f, 0.71f, 1.0f, 0.08f);
        for (int i = 1; i < 8; i++)
        {
            float t = i / 8.0f;
            DrawLine(
                new Vector2(mapRect.Position.X + side * t, mapRect.Position.Y),
                new Vector2(mapRect.Position.X + side * t, mapRect.End.Y),
                gridColor, 1.0f
            );
            DrawLine(
                new Vector2(mapRect.Position.X, mapRect.Position.Y + side * t),
                new Vector2(mapRect.End.X, mapRect.Position.Y + side * t),
                gridColor, 1.0f
            );
        }

        // 2. 西北河谷雷达低空盲区斜线带与北山脊棱线
        Vector2 ridgeA = NormalizedToScreen(new Vector2(0.28f, 0.36f), mapRect);
        Vector2 ridgeB = NormalizedToScreen(new Vector2(0.68f, 0.37f), mapRect);
        DrawLine(ridgeA, ridgeB, Color.FromHtml("#f5cf47"), 2.0f);

        // 3. 来袭走廊虚线（西北巡航导弹走廊 + 东路无人机走廊）
        Vector2 nwEntry = NormalizedToScreen(new Vector2(0.08f, 0.16f), mapRect);
        Vector2 waterPos = NormalizedToScreen(new Vector2(0.39f, 0.44f), mapRect);
        DrawDashedLine(nwEntry, waterPos, Color.FromHtml("#ff5b4f"), 2.0f, 8.0f);

        Vector2 eastEntry = NormalizedToScreen(new Vector2(0.92f, 0.41f), mapRect);
        Vector2 plantPos = NormalizedToScreen(new Vector2(0.58f, 0.62f), mapRect);
        DrawDashedLine(eastEntry, plantPos, Color.FromHtml("#ff5b4f"), 2.0f, 8.0f);

        // 4. 我方单位射程圈与北约友军矩形符号
        foreach (var u in _units)
        {
            Vector2 p = NormalizedToScreen(u.NormalizedPos, mapRect);
            bool isSelected = (u.RosterId == _selectedRosterId);
            float radiusPx = (float)(u.RangeKm / 40.0) * side;
            Color ringColor = u.IsSensor
                ? new Color(0.5f, 0.88f, 0.88f, isSelected ? 0.38f : 0.16f)
                : new Color(0.37f, 0.71f, 1.0f, isSelected ? 0.45f : 0.18f);
            DrawArc(p, radiusPx, 0.0f, Mathf.Tau, 64, ringColor, isSelected ? 1.8f : 1.0f);

            Rect2 box = new Rect2(p - new Vector2(11, 8), new Vector2(22, 16));
            DrawRect(box, Color.FromHtml("#0d1520"), true);
            DrawRect(box, isSelected ? Color.FromHtml("#f5cf47") : Color.FromHtml("#5fb6ff"), false, isSelected ? 2.2f : 1.5f);
        }

        // 5. 保卫目标（白色菱形地标）
        foreach (var s in _structures)
        {
            Vector2 p = NormalizedToScreen(s.NormalizedPos, mapRect);
            Rect2 box = new Rect2(p - new Vector2(12, 12), new Vector2(24, 24));
            DrawRect(box, Color.FromHtml("#0d1520"), true);
            DrawRect(box, Color.FromHtml("#e7edf5"), false, 2.0f);
        }
    }

    private Vector2 NormalizedToScreen(Vector2 norm, Rect2 mapRect)
    {
        return mapRect.Position + new Vector2(norm.X * mapRect.Size.X, norm.Y * mapRect.Size.Y);
    }

    private Vector2 ScreenToNormalized(Vector2 screenPt)
    {
        Rect2 mapRect = CurrentMapRect();
        float side = mapRect.Size.X;
        if (side <= 1.0f)
        {
            return new Vector2(0.5f, 0.5f);
        }
        return (screenPt - mapRect.Position) / side;
    }

    private MapUnitMarker? PickUnit(Vector2 mousePos, float maxRadiusPx)
    {
        Rect2 mapRect = CurrentMapRect();

        MapUnitMarker? best = null;
        float bestDistSq = maxRadiusPx * maxRadiusPx;
        foreach (var u in _units)
        {
            Vector2 p = NormalizedToScreen(u.NormalizedPos, mapRect);
            float dx = p.X - mousePos.X;
            float dy = p.Y - mousePos.Y;
            float d2 = dx * dx + dy * dy;
            if (d2 < bestDistSq)
            {
                bestDistSq = d2;
                best = u;
            }
        }
        return best;
    }

    private void ClampPan()
    {
        float limit = (float)(Math.Max(Size.X, Size.Y) * 0.45 * _zoom);
        _panOffsetPx.X = Mathf.Clamp(_panOffsetPx.X, -limit, limit);
        _panOffsetPx.Y = Mathf.Clamp(_panOffsetPx.Y, -limit, limit);
    }

    private void UpdateDockLabel()
    {
        var zoomResetBtn = GetNodeOrNull<Button>("ZoomDock/VBox/BtnDockZoomReset");
        if (zoomResetBtn != null)
        {
            zoomResetBtn.Text = $"{Mathf.RoundToInt((float)(_zoom * 100.0))}%";
        }
    }
}
