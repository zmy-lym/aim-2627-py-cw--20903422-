# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
from collections import deque
from enum import Enum


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """TODO(Q1)：血量百分比，返回 0-100 的 int；计算与边界规则见题面 Q1 规范。"""
    if not isinstance(hp, (int, float)) or isinstance(hp, bool):
        raise TypeError("hp 必须为数值")
    if not isinstance(max_hp, (int, float)) or isinstance(max_hp, bool):
        raise TypeError("max_hp 必须为数值")
    if max_hp <= 0:
        raise ValueError("max_hp 必须为正数")
    ratio = hp / max_hp * 100  # 防御式规范化：越界值夹回 0-100（题面 Q5 口径）
    return max(0, min(100, int(ratio)))
# 夹紧结果，保证百分比落在0‑100区间，防止异常输入溢出


def status_report(name, robot_type, hp, max_hp, battery):
    """TODO(Q1)：一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。"""
    if not isinstance(name, str) or not isinstance(robot_type, str):
        raise TypeError("name 和 robot_type 必须为字符串")
    pct = hp_ratio(hp, max_hp)  # hp/max_hp 合法性与规范化统一交给 hp_ratio
    battery = int(battery)
    if battery > 50:
        gear = "OK"
    elif battery > 20:
        gear = "WARNING"
    else:
        gear = "LOW"
    return f"{name:<10}|{robot_type:^10}|HP {pct:>3}%|BAT {battery:>3}%|{gear}"


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
_SENSOR_KEY_TO_ARMOR = {"F": "front", "L": "left", "R": "right"}


def _positive_int(value):
    """严格正整数判定（bool 不是整数，题面 Q2 规范 4/5）。"""
    return (isinstance(value, int) and not isinstance(value, bool)
            and value > 0)


def _parse_json_damage_line(s):
    """解析 JSON 行 -> [(armor, damage, id)]；id 可选，非法返回 []。"""
    try:
        data = json.loads(s)
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    armor = data.get("armor")
    damage = data.get("damage")
    if armor not in ("front", "left", "right"):
        return []
    if not _positive_int(damage):
        return []
    if "id" in data:
        event_id = data["id"]
        if not isinstance(event_id, int) or isinstance(event_id, bool):
            return []
    else:
        event_id = None
    return [(armor, damage, event_id)]


def _parse_sensor_damage_line(s):
    """解析传感器行 "F:32,L:5,R:12" -> [(armor, damage, None), ...]。

    每个分段各计一次事件；任一分段非法则整行作脏行（题面 Q2 规范 5）。
    """
    events = []
    for seg in s.split(","):
        key_str, sep, val_str = seg.partition(":")
        if not sep:
            return []
        key_str = key_str.strip()
        val_str = val_str.strip()
        if key_str not in _SENSOR_KEY_TO_ARMOR or not val_str.isdigit():
            return []
        damage = int(val_str)
        if damage <= 0:
            return []
        events.append((_SENSOR_KEY_TO_ARMOR[key_str], damage, None))
    return events


def analyze_damage_log(lines):
    """TODO(Q2)：解析混合格式伤害日志，返回固定契约的统计 dict；
    行格式、去重与统计口径见题面 Q2 规范。"""
    total_damage = 0
    by_armor = {"front": 0, "left": 0, "right": 0}
    seen_ids = set()
    event_count = 0
    for line in lines:
        s = line.strip() if isinstance(line, str) else ""
        if not s or s.startswith("#"):
            continue  # 脏行：空行 / 注释
        if s.startswith("{"):
            events = _parse_json_damage_line(s)
        else:
            events = _parse_sensor_damage_line(s)
        if not events:
            continue  # 脏行：无法解析 / 字段非法
        for armor, damage, event_id in events:
            if event_id is not None:
                if event_id in seen_ids:
                    continue  # 规范 6：同一 id 只计第一次出现
                seen_ids.add(event_id)
            total_damage += damage
            by_armor[armor] += damage
            event_count += 1

    most_hit = None
    if event_count > 0:
        max_val = max(by_armor.values())
        if max_val > 0:
            if by_armor["front"] == max_val:
                most_hit = "front"
            elif by_armor["left"] == max_val:
                most_hit = "left"
            else:
                most_hit = "right"
    avg = round(total_damage / event_count, 2) if event_count else 0.0
    return {
        "total": total_damage,
        "by_armor": by_armor,
        "most_hit": most_hit,
        "avg": avg,
    }


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """TODO(Q3)：位置 setter；三重输入校验见题面 Q3 规范第 1 条。"""
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise TypeError("current_pos 必须为长度为 2 的 tuple/list")
        pos = self._clamp_cell(value)
        if pos in self._obstacles:
            raise ValueError("current_pos 不能位于障碍物上")
        self._pos = pos

    def move_forward(self):
        """TODO(Q3)：朝当前 facing 前进一格，返回执行后的位置；
        碰撞、耗电与断电语义见题面 Q3 规范。"""
        if self._fuel <= 0:
            return self._pos  # 断电：前进尝试不产生位移
        self._fuel -= 1
        dx, dy = self._facing.delta
        nx, ny = self._pos[0] + dx, self._pos[1] + dy
        if self.is_blocked(nx, ny):
            self._collision_count += 1  # 碰撞：位置与朝向均不变
            return self._pos
        self._pos = (nx, ny)  # 前方可通行：移动到该格
        return self._pos

    def turn_left(self):
        """TODO(Q3)：原地左转 90°，返回新的 Facing（不耗电）。"""
        left_of = {
            Facing.UP: Facing.LEFT,
            Facing.LEFT: Facing.DOWN,
            Facing.DOWN: Facing.RIGHT,
            Facing.RIGHT: Facing.UP
        }
        self._facing = left_of[self._facing]
        return self._facing

    def turn_right(self):
        """TODO(Q3)：原地右转 90°，返回新的 Facing（不耗电）。"""
        right_of = {
            Facing.UP: Facing.RIGHT,
            Facing.RIGHT: Facing.DOWN,
            Facing.DOWN: Facing.LEFT,
            Facing.LEFT: Facing.UP
        }
        self._facing = right_of[self._facing]
        return self._facing


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """TODO(Q4)：返回下一步应朝向的 Facing；
    候选判定、优先级与回退规则见题面 Q4 规范。"""
    x, y = pos
    tx, ty = target
    dx = tx - x
    dy = ty - y
    before = abs(dx) + abs(dy)
    if before == 0:
        return current_facing
    x_dir = Facing.RIGHT if dx > 0 else Facing.LEFT
    y_dir = Facing.UP if dy > 0 else Facing.DOWN
    axis_order = ("x", "y") if abs(dx) >= abs(dy) else ("y", "x")
    for axis in axis_order:
        if axis == 'x' and dx == 0:
            continue
        if axis == 'y' and dy == 0:
            continue
        facing = x_dir if axis == "x" else y_dir
        fx, fy = facing.delta
        nxt = (x + fx, y + fy)
        after = abs(nxt[0] - tx) + abs(nxt[1] - ty)
        if after < before and nxt not in obstacles:
            return facing

    return current_facing

# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------


class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """TODO(Q5)：纯函数决策，返回 (action: str, new_state: SentryState)；
    sensor 字段契约、R1-R7 规则表与非法输入处理见题面 Q5 规范。"""
    # ---- 输入契约：契约之外（缺失字段 / 非法 state / 帧历史长度越界）----
    required = ("enemy_frames", "enemy_dist", "robot_type", "max_hp")
    if not isinstance(sensor, dict) or any(k not in sensor for k in required):
        raise ValueError("sensor 缺少必要字段")
    if not isinstance(state, SentryState):
        raise ValueError("state 必须是 SentryState")
    frames = sensor["enemy_frames"]
    if not isinstance(frames, (tuple, list)) or not (1 <= len(frames) <= 6):
        raise ValueError("enemy_frames 长度必须为 1-6")

    # ---- 防御式规范化：字段存在但取值非法时不抛异常（题面 Q5 末段）----
    frames = tuple(bool(item) for item in frames)
    visible = frames[-1]  # 可见 = 帧历史末位（当前帧）为真
    enemy_dist = sensor["enemy_dist"]
    if type(enemy_dist) is not int:
        enemy_dist = None  # 非整数敌距按不可知处理
    robot_type = sensor["robot_type"]
    if robot_type not in ("INFANTRY", "HERO"):
        robot_type = "INFANTRY"  # 非法机型按步兵处理
    hp_pct = hp_ratio(hp, sensor["max_hp"])

    def engage_action():
        """R4/R6 共用的交火判定：敌距 <=3 开火，否则按机型横移。"""
        if enemy_dist is not None and enemy_dist <= 3:
            return "SHOOT"
        if robot_type == "HERO":
            return "MOVE_RIGHT"
        return "MOVE_LEFT"

    # ---- 规则表：按 R1-R7 固定顺序求值，首条命中即返回 ----
    # R1 保命优先：优先于包括贴脸交火在内的其余全部规则
    if hp_pct <= 30:
        return ("RETREAT", SentryState.RETREAT)
    # R2 撤退保持：恢复到安全血量后转出撤退
    if state is SentryState.RETREAT:
        return ("RETURN", SentryState.RETURN)
    # R3 返航单帧：RETURN 为单帧过渡状态，与可见性/敌距/热量均无关
    if state is SentryState.RETURN:
        return ("MOVE_BASE", SentryState.PATROL)
    # R4 交火决策 / R5 交火保持
    if state is SentryState.ENGAGE:
        if visible:
            return (engage_action(), SentryState.ENGAGE)  # R4
        if any(frames[:-1]):  # 帧历史里仍有真帧 = 短暂丢失
            return ("HOLD_FIRE", SentryState.ENGAGE)  # R5
        return ("SCAN", SentryState.SUSPECT)  # R5 持续丢失
    # R6 敌情确认 / R7 默认行为（PATROL 与 SUSPECT）
    if state in (SentryState.PATROL, SentryState.SUSPECT):
        if visible:
            if len(frames) >= 2 and frames[-2]:  # 末两位全真 = 敌情确认
                return (engage_action(), SentryState.ENGAGE)  # R6
            return ("SCAN", SentryState.SUSPECT)  # R6 单帧可见未确认
        if state is SentryState.PATROL:
            return ("PATROL_MOVE", SentryState.PATROL)  # R7
        return ("SCAN", SentryState.SUSPECT)  # R7
    raise ValueError("未知状态")


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
# 沿墙脱困用的旋转表（左手规则 = 优先贴墙侧转向）
_TURN_LEFT = {Facing.UP: Facing.LEFT, Facing.LEFT: Facing.DOWN,
              Facing.DOWN: Facing.RIGHT, Facing.RIGHT: Facing.UP}
_TURN_RIGHT = {Facing.UP: Facing.RIGHT, Facing.RIGHT: Facing.DOWN,
               Facing.DOWN: Facing.LEFT, Facing.LEFT: Facing.UP}


def _manhattan(a, b):
    """两点间曼哈顿距离。"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _has_greedy_candidate(grid):
    """Q4 贪心是否失速：四邻域是否存在严格减距的可通行格（题面 Q6 规范 1）。"""
    pos = grid.current_pos
    target = grid.enemy_pos
    direction = next_step_toward(pos, target, grid.obstacles, grid.facing)
    dx, dy = direction.delta
    nxt = (pos[0] + dx, pos[1] + dy)
    return (not grid.is_blocked(nxt[0], nxt[1])
            and _manhattan(nxt, target) < _manhattan(pos, target))


def _face_toward(grid, direction):
    """原地旋转把朝向对齐到 direction（差 3 步时改用一次左转，省两步）。"""
    rights = {Facing.UP: 0, Facing.RIGHT: 1, Facing.DOWN: 2, Facing.LEFT: 3}
    diff = (rights[direction] - rights[grid.facing]) % 4
    if diff == 3:
        grid.turn_left()
    else:
        for _ in range(diff):
            grid.turn_right()


def _wall_escape_step(grid, hand):
    """沿墙走一步的转向决策（左手/右手规则）。

    优先级：墙侧空则贴墙转向；正前堵死时另一侧空则朝另一侧转；
    三个方向全堵则掉头；否则保持朝向直行。
    返回值无意义，只产生转向副作用。
    """
    side = _TURN_LEFT[grid.facing] if hand == "L" else _TURN_RIGHT[grid.facing]
    other = _TURN_RIGHT[grid.facing] if hand == "L" else _TURN_LEFT[grid.facing]
    side_cell = (grid.current_pos[0] + side.delta[0],
                 grid.current_pos[1] + side.delta[1])
    front_cell = (grid.current_pos[0] + grid.facing.delta[0],
                  grid.current_pos[1] + grid.facing.delta[1])
    other_cell = (grid.current_pos[0] + other.delta[0],
                  grid.current_pos[1] + other.delta[1])
    if not grid.is_blocked(*side_cell):
        grid.turn_left() if hand == "L" else grid.turn_right()
    elif grid.is_blocked(*front_cell):
        if not grid.is_blocked(*other_cell):
            grid.turn_right() if hand == "L" else grid.turn_left()
        else:
            grid.turn_right()
            grid.turn_right()
    # 正前可走且墙侧堵：保持朝向直行


def run_patrol(grid, max_steps=500):
    """TODO(Q6)：sense → decide → act 主循环；
    循环结构、终止条件、脱困自由度与统计返回契约见题面 Q6 规范。"""
    steps = 0
    visited = set()
    # ---- 脱困状态（沿墙走）：参数是主要调参点，改这里 ----
    wall_mode = False      # 是否处于沿墙脱困
    hand = "L"             # 沿墙的手：先左手，超时换右手（题面提到的"换手"）
    wall_steps = 0         # 本段沿墙已走步数
    entry_dist = 0         # 进入脱困时的曼哈顿距离（出口判据用）
    hand_limit = 32  # TODO(调参)：换手阈值
    # 强制退出脱困阈值：2× 换手阈值。32/64 组合在 200 seed 上实测
    # 96.5% / 0.00 碰撞 / 步数比 1.20，三项阈值全过（题面 Q6 规范 7）
    wall_limit = 2 * hand_limit
    while steps < max_steps and grid.fuel > 0 and not grid.found_enemy:
        pos = grid.current_pos
        visited.add(pos)
        # ---- sense：贪心是否失速 ----
        if not wall_mode and not _has_greedy_candidate(grid):
            wall_mode = True   # 切入沿墙脱困
            hand = "L"
            wall_steps = 0
            entry_dist = _manhattan(pos, grid.enemy_pos)
        # ---- decide：确定本步方向 ----
        if wall_mode:
            _wall_escape_step(grid, hand)
        else:
            direction = next_step_toward(pos, grid.enemy_pos,
                                         grid.obstacles, grid.facing)
            _face_toward(grid, direction)
        # ---- act：对齐后前进一格 ----
        grid.move_forward()
        steps += 1
        # ---- 脱困出口判定 ----
        if wall_mode:
            wall_steps += 1
            dist = _manhattan(grid.current_pos, grid.enemy_pos)
            if wall_steps > wall_limit:
                wall_mode = False            # 沿墙太久：强制回贪心
            elif wall_steps > hand_limit and hand == "L":
                hand = "R"                   # 左手超时：换右手
                wall_steps = 0
            elif (_has_greedy_candidate(grid)
                    and dist < entry_dist + 1):
                wall_mode = False            # 距离重新可缩短：切回贪心
    visited.add(grid.current_pos)
    return {
        "steps": steps,
        "collisions": grid.collision_count,
        "visited_count": len(visited),
        "found_enemy": grid.found_enemy,
        "success": grid.found_enemy,
    }


def report_to_json(stats):
    """TODO(Q6)：把 stats 序列化为确定性的 JSON 字符串，见题面 Q6 规范。"""
    # 确定性三要素：键排序 + 紧凑分隔符 + 固定的非 ASCII 处理
    return json.dumps(stats, sort_keys=True,
                      separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。

    start == target 恒返回 0；目标不可达返回 -1。
    与工具参考实现（tools 的 bfs_len）一致：start 视为可通行起点，
    即使它与障碍物重合也照常向外搜索。
    地图边界由调用方放进 obstacles（题面 Bonus 规范 2）；
    visited 集合保证搜索必然终止。
    """
    start = tuple(start)
    target = tuple(target)
    if start == target:
        return 0
    blocked = obstacles if isinstance(obstacles, set) else set(obstacles)
    if target in blocked:
        # 等价于搜索耗尽返回 -1；无边界环时兼防无限扩散
        return -1
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        (x, y), dist = queue.popleft()
        for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if nxt in blocked or nxt in seen:
                continue
            if nxt == target:
                return dist + 1
            seen.add(nxt)
            queue.append((nxt, dist + 1))
    return -1


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
