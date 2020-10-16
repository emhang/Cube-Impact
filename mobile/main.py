from __future__ import division
from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.core.window import Window
import random
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
import time
from kivy.core.audio import SoundLoader
import os
from threading import Thread

# 获取绝对路径，避免打包后出现错误
def getPath(fileName):
    cur_path = os.path.abspath(os.curdir)
    path = cur_path + '/' + fileName
    return path

# 音频文件的路径
move_audio = getPath('se/move.wav')  # 左右移动
change_audio = getPath('se/rotate.wav')  # 交换颜色
drop_audio = getPath('se/collapse.wav')  # 方块落地
destroy_audio = getPath('se/medal.wav')  # 普通消除
special_audio = getPath('se/gem.wav')  # 银色方块消除
attack_audio = getPath('se/attack.wav')  # 攻击
defend_audio = getPath('se/erase1.wav')  # 防御
victory_audio = getPath('se/excellent.wav')  # 获胜
fail_audio = getPath('se/fail.wav')  # 失败
pause_audio = getPath('se/pause.wav')  # 暂停
continue_audio = getPath('se/b2b_continue.wav')  # 继续
confirm_audio = getPath('se/b2b_start.wav')  # 确定
bgm_audio = getPath('se/bgm.ogg')  # 背景音乐（取自Nihon Falcomポムっと，待替换为原创音乐）

#cur_path = os.path.abspath(os.curdir)

bgm_status = False  # 背景音乐状态通过全局变量控制

# 背景音乐播放函数
def bgm_play():
    bgm_sound = SoundLoader.load(bgm_audio)
    bgm_sound.loop = True

    while True:
        if bgm_sound.state == 'stop' and bgm_status:
            bgm_sound.play()
        elif bgm_sound.state == 'play' and not bgm_status:
            bgm_sound.stop()
        time.sleep(0.5)

# 通过子线程控制背景音乐播放
bgm_thread = Thread(target=bgm_play)
bgm_thread.setDaemon(True)
bgm_thread.start()

# 音效播放函数
def audio_play_s(path):
    t = Thread(target=audio_play, args=(path,))
    t.setDaemon(True)
    t.start()

# 音效播放子线程化
def audio_play(path):
    sound = SoundLoader.load(path)
    sound.play()

# 全局变量：可选颜色列表、AI类型、游戏宽度（列数）、高度（行数）
all_color_list = (((1, 0, 0), (0, 1, 0), (0, 0.4, 1), (1, 1, 0)), (0.9, 0.9, 0.9))
ai_type = 1
GRID_WIDTH = 7
GRID_HEIGHT = 12

# 圆角按键类
class RoundedButton(Button):

    def __init__(self, back_color=(.5, .5, .5, 1), radius=dp(15), **kwargs):
        super(RoundedButton, self).__init__(**kwargs)
        self.back_color = back_color
        self.radius = radius
        self.bind(size=self.redraw)
        self.bind(on_press=self.redraw)
        self.bind(on_release=self.redraw)
        self.bind(state=self.redraw)

    # 绘制函数，在按键画布上绘制圆角矩形，并根据按键状态改变颜色
    def redraw(self, *args):
        self.background_color = (0, 0, 0, 0)
        self.canvas.before.clear()
        with self.canvas.before:
            if self.disabled:
                color = (self.back_color[0], self.back_color[1], self.back_color[2], self.back_color[3] * 0.4)
                Color(*color)
            elif self.state == 'normal':
                Color(*self.back_color)
            else:
                color = (self.back_color[0], self.back_color[1], self.back_color[2], self.back_color[3] * 0.7)
                Color(*color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius,])

# Cube类，确定方块的行、列、颜色
class Cube:
    def __init__(self, row, col, color = -1):
        self.row = row
        self.col = col
        self.color = color

# GameState类，确定游戏的基本信息
class GameState:
    def __init__(self, type):
        self.type = type  # 游戏类型，0:AI；1:人类
        self.reset()

    def reset(self):
        # 若为AI玩家，设定自动指令序列、目标位置、攻击判定时间、AI行动间隔等信息
        if self.type == 0:
            self.auto_order = []
            self.auto_target = 3
            self.action_decide_time = time.time()
            self.ai_type = ai_type
            self.ai_count = 0
            if ai_type == 1:
                self.ai_speed = 80
            elif ai_type == 2:
                self.ai_speed = 40
            elif ai_type == 3:
                self.ai_speed = 20

        # 生成活动方块和下一组活动方块的颜色
        self.active_cubes = (Cube(12, 3, random.randint(0, len(all_color_list[0]) - 1)),
                             Cube(13, 3, random.randint(0, len(all_color_list[0]) - 1)))
        self.next_color = (random.randint(0, len(all_color_list[0]) - 1),
                           random.randint(0, len(all_color_list[0]) - 1))

        self.cubes = [[], [], [], [], [], [], []]  # 游戏下方的方块列表
        # 随机生成3行方块作为初始方块
        new_cubes = self.generate_cube(3)
        self.cubes = new_cubes

        self.basic_speed = 0.02  # 游戏的基本掉落速度
        self.speed = self.basic_speed  # 游戏的实际进行速度
        self.game_status = 'start'  # 游戏状态，起始为'start'
        self.win = True  # 游戏获胜状态，失败时为False
        self.delete_list = [[], []]  # 待消除列表，包括普通颜色方块和特殊颜色方块
        self.blink_count = 0  # 闪烁计数，决定闪烁进程
        self.blink = True  # 闪烁boolean，决定闪烁显示状态
        self.score = 0  # 游戏得分
        self.round = 0  # 游戏得分轮次
        self.round_score = 0  # 单轮得分
        self.add_score = 0  # 已加上的得分
        self.basic_score = 0  # 基础得分，消除1个方块=1分
        self.bonus_score = 0  # bonus得分，每轮消除超过3个方块的额外得分，以及特殊方块的额外分数
        self.chain_score = 0  # chain得分，每多一个消除轮次增加得分
        self.clear_cubes = 0  # 已消除的方块数量，决定游戏下方自动升起的行数
        self.down_cubes = 0  # 已落下的方块数量，决定游戏基础速度的增加
        self.new_line = 0  # 被攻击的升起行数
        self.delete_line = 0  # 防御的消除行数
        self.action_time = time.time()  # 攻防的动作起始时间
        self.action = False  # 是否存在攻防行为，若存在攻防行为，则原方块继续从头掉落，否则调用下一组颜色作为新的活动方块
        self.action_decide_time = time.time()  # AI的动作判定时间

    # 向左移动
    def move_left(self):
        self.active_cubes[0].col -= 1
        if self.check_collision():
            self.active_cubes[0].col += 1
        else:
            self.active_cubes[1].col -= 1
            if self.type != 0:
                audio_play_s(move_audio)

    # 向右移动
    def move_right(self):
        self.active_cubes[0].col += 1
        if self.check_collision():
            self.active_cubes[0].col -= 1
        else:
            self.active_cubes[1].col += 1
            if self.type != 0:
                audio_play_s(move_audio)

    # 向下移动，若发生碰撞，则合并方块
    def move_down(self):
        self.active_cubes[0].row -= self.speed
        if self.check_collision():
            self.active_cubes[0].row += self.speed
            self.affix_cube()
        else:
            self.active_cubes[1].row -= self.speed

    # 交换颜色
    def change(self):
        self.active_cubes[0].color, self.active_cubes[1].color = self.active_cubes[1].color, self.active_cubes[0].color
        if self.type != 0:
            audio_play_s(change_audio)

    # 判断是否撞到方块或撞墙
    def check_collision(self):
        collision = False
        row, col = self.active_cubes[0].row, self.active_cubes[0].col
        if col >= GRID_WIDTH or col < 0:
            collision = True
        elif row < len(self.cubes[col]):
            collision = True
        return collision

    # 合并方块，将活动方块加入底部方块，进入"auto_move"状态
    def affix_cube(self):
        col = self.active_cubes[0].col
        self.active_cubes[0].row = len(self.cubes[col])
        self.active_cubes[1].row = len(self.cubes[col]) + 1
        self.cubes[self.active_cubes[0].col].append(self.active_cubes[0])
        self.cubes[self.active_cubes[0].col].append(self.active_cubes[1])
        if self.type != 0:
            audio_play_s(drop_audio)
        self.down_cubes += 2
        self.game_status = 'auto_move'

    # "auto_move"函数，底端方块进行自动移动、归位
    def auto_move(self):
        # 判断是否存在方块的row值与实际在列表中的位置不符，若有，则按照0.15的速度移动，直到相符
        move_cubes = 0
        for col, this_col in enumerate(self.cubes):
            for row, this_cube in enumerate(this_col):
                if this_cube.row > row:
                    this_cube.row -= 0.15
                    if this_cube.row < row:
                        this_cube.row = row
                    move_cubes += 1
                elif this_cube.row < row:
                    this_cube.row += 0.15
                    if this_cube.row > row:
                        this_cube.row = row
                    move_cubes += 1

        # move_cubes为0，代表全部已经归位，此时进行消除判断
        if move_cubes == 0:
            self.cube_decide()
            # 若无可消除的方块
            if len(self.delete_list[0]) == 0:
                # 若中间列达到顶端且无防御行为，则游戏失败
                if len(self.cubes[3]) >= GRID_HEIGHT and self.delete_line == 0:
                    self.game_status = 'game_over'
                    self.win = False

                # 否则进行自动升起判定
                else:
                    # 自动升起行数由被攻击的行数和根据消除方块的数量计算的行数相加构成
                    time_line = int(self.clear_cubes // 9)
                    new_line = time_line + self.new_line
                    if new_line > 0:
                        new_cubes = self.generate_cube(new_line)
                        for col in range(7):
                            self.cubes[col] = new_cubes[col] + self.cubes[col]
                        self.clear_cubes -= time_line * 9
                        if self.clear_cubes < 0:
                            self.clear_cubes = 0
                        if self.new_line > 0:
                            self.new_line = 0

                    # 若不需要升起且有防御行为，则进入'blink'状态
                    elif self.delete_line > 0:
                        self.game_status = 'blink'
                        self.blink_count = 0
                        self.blink = False
                        self.round_score = 0
                        self.add_score = 0

                    # 否则回到'active'状态
                    else:
                        self.basic_speed = 0.01 * (self.down_cubes / 20 + 2)
                        if self.basic_speed > 0.25:
                            self.basic_speed = 0.25
                        self.speed = self.basic_speed
                        # 若发生了攻击或防御行为，则调用当前方块从头掉落，否则调用下一个方块的颜色并重新生成
                        if not self.action:
                            self.active_cubes = (Cube(12, 3, self.next_color[0]),
                                                 Cube(13, 3, self.next_color[1]))
                            self.next_color = (random.randint(0, len(all_color_list[0]) - 1),
                                               random.randint(0, len(all_color_list[0]) - 1))
                        else:
                            self.active_cubes[0].col = 3
                            self.active_cubes[0].row = 12
                            self.active_cubes[1].col = 3
                            self.active_cubes[1].row = 13
                            self.action = False

                        self.round = 0
                        self.game_status = 'active'

            # 若存在可消除的方块，计算得分并进入'blink'状态
            else:
                if self.type != 0:
                    audio_play_s(destroy_audio)
                self.game_status = 'blink'
                self.blink_count = 0
                self.blink = False
                self.basic_score = len(self.delete_list[0])
                if self.basic_score > 3:
                    self.bonus_score = self.basic_score - 3
                else:
                    self.bonus_score = 0
                if len(self.delete_list[1]) > 0:
                    if self.type != 0:
                        audio_play_s(special_audio)
                    self.bonus_score += len(self.delete_list[1]) * 100
                if self.round < 5:
                    self.chain_score = self.round * 5
                else:
                    self.chain_score = 25
                self.round += 1
                self.round_score = self.basic_score + self.bonus_score + self.chain_score
                self.add_score = 0

    # 方块消除延伸判定，输入信息为判定需要消除的方块位置与颜色
    def cube_destroy(self, pos, color):
        # 若已在列表中，则不再继续递归
        if pos in self.delete_list[0]:
            return

        self.delete_list[0].append(pos)  # 在列表中加入该方块位置
        # 获取相邻方块位置，如果它们与该方块颜色相同或为特殊方块，则消除
        neighbours = [(pos[0] - 1, pos[1]),
                      (pos[0] + 1, pos[1]),
                      (pos[0], pos[1] - 1),
                      (pos[0], pos[1] + 1)]
        for position in neighbours:
            if position[0] not in range(7) or position[1] not in range(len(self.cubes[position[0]])):
                continue
            if color == self.cubes[position[0]][position[1]].color:
                self.cube_destroy(position, color)  # 若为需要消除的普通方块，则递归
            elif self.cubes[position[0]][position[1]].color == -1:
                if position not in self.delete_list[1]:
                    self.delete_list[1].append(position)

    # 判定cubes中需要消除的方块
    def cube_decide(self):
        self.delete_list = [[], []]
        for col, this_col in enumerate(self.cubes):
            for row, this_cube in enumerate(this_col):
                color = this_cube.color
                # 当相邻方块有2个与自身颜色相同，则是需要消除的方块
                neighbours = [(col - 1, row),
                              (col + 1, row),
                              (col, row - 1),
                              (col, row + 1)]
                count = 0
                for position in neighbours:
                    if position[0] not in range(7) or position[1] not in range(len(self.cubes[position[0]])):
                        continue
                    if color == self.cubes[position[0]][position[1]].color:
                        count += 1
                if count >= 2:
                    self.cube_destroy((col, row), color)

    # 闪烁进程函数
    def blink_process(self):
        # 若本轮消除存在得分，则将得分逐帧逐渐加入score中，增强动态感
        if self.round_score > 0:
            add_score = int(self.round_score * self.blink_count / 30)
            if add_score > self.add_score:
                self.score += (add_score - self.add_score)
                if self.score > 999:
                    self.score = 999
                self.add_score = add_score

        # 每帧进行计数，每5帧切换一次显示状态
        self.blink_count += 1
        if self.blink_count % 5 == 0:
            self.blink = not self.blink

        # 达到30帧结束闪烁，补齐未加的分数，将分数数据清空，同时在cubes中删除待消除的方块，回到'automove'状态
        if self.blink_count >= 30:
            if self.round_score > 0:
                if self.round_score > self.add_score:
                    self.score += (self.round_score - self.add_score)
                    if self.score > 999:
                        self.score = 999
                self.round_score = 0
                self.add_score = 0
                self.basic_score = 0
                self.bonus_score = 0
                self.chain_score = 0
            cubes_ori = self.cubes
            self.cubes = [[], [], [], [], [], [], []]
            if self.new_line > 0:
                for col, this_col in enumerate(cubes_ori):
                    for row, this_cube in enumerate(this_col):
                        if (col, row) not in self.delete_list[0] and (col, row) not in self.delete_list[1]:
                            self.cubes[col].append(this_cube)
            else:
                for col, this_col in enumerate(cubes_ori):
                    for row, this_cube in enumerate(this_col):
                        if (col, row) not in self.delete_list[0] and (col, row) not in self.delete_list[1] and row >= self.delete_line:
                            self.cubes[col].append(this_cube)
                self.delete_line = 0

            self.clear_cubes += len(self.delete_list[0]) + len(self.delete_list[1])
            self.game_status = 'auto_move'

    # 获取邻近方块的信息，返回值为与输入方块颜色相同的方块位置及数量
    def neighbour_color(self, pos, color, cubes):
        count = 0
        same_color_pos = []
        for this_col in cubes:
            for this_cube in this_col:
                if (abs(this_cube.col - pos[0]) == 1 and this_cube.row == pos[1]) or (abs(this_cube.row - pos[1]) == 1 and this_cube.col == pos[0]):
                    if this_cube.color == color:
                        same_color_pos.append((this_cube.col, this_cube.row))
                        count += 1
        return same_color_pos, count

    # 生成随机line行方块，这些方块不会自行消除
    def generate_cube(self, line):
        # 首先将原cubes的最低行加入new_cubes
        new_cubes = [[], [], [], [], [], [], []]
        for col in range(7):
            if len(self.cubes[col]) > 0:
                new_cubes[col].append(self.cubes[col][0])

        # 从左至右，从下至上生成随机方块
        for col in range(7):
            for row in range(-line, 0):
                while True:
                    # 先判定是否是特殊方块，否则随机选择一个普通颜色
                    p = random.random()
                    if p < 0.045:
                        color = -1
                    else:
                        color = random.randint(0, len(all_color_list[0]) - 1)

                    # 若为特殊方块，则直接确定；否则判相邻方块的信息，若可能出现自动消除，则重新生成
                    if color == -1:
                        break
                    else:
                        pos, count = self.neighbour_color((col, row), color, new_cubes)
                        if count >= 2:
                            continue
                        elif count == 1:
                            if self.neighbour_color(pos[0], color, new_cubes)[1] > 0:
                                continue
                            else:
                                break
                        else:
                            break
                new_cubes[col].append(Cube(row, col, color))

        # 最后清除一开始加入的cubes最低行方块
        for col in range(7):
            if len(self.cubes[col]) > 0:
                new_cubes[col].pop(0)

        return new_cubes

    # AI基本操作行为函数，now_row、now_col代表活动方块所处的行数、列数
    def ai_decide(self, now_row, now_col):
        active_cubes = self.active_cubes
        cubes = self.cubes
        score_predict = {}  # 每一种操作的价值得分，以字典的方式记录
        score_distribution = [1, 4, 7, 20, 7, 4, 1]  # 每一列的基础价值不同，越靠近中心，则价值越大

        # 按照2、1、0、4、5、6、3列的顺序判断可能的价值分数
        for col in [2, 1, 0, 4, 5, 6, 3]:
            # 若已经记录在字典中，则跳过
            if (col, 0) in score_predict:
                continue
            else:
                # 如果该列处于活动方块当前位置以下，则进行价值判断
                if len(cubes[col]) < now_row:
                    # 将活动方块加入此列，根据此时每列方块的增、减决定得分，其中特殊方块额外价值为20分，计算完毕后将相关数据还原
                    cubes[col].append(Cube(len(cubes[col]), col, active_cubes[0].color))
                    cubes[col].append(Cube(len(cubes[col]) + 1, col, active_cubes[1].color))
                    self.cube_decide()
                    score = - score_distribution[col] * 2
                    for (c, r) in self.delete_list[0]:
                        score += score_distribution[c]
                    score += 20 * len(self.delete_list[1])
                    score_predict[(col, 0)] = score
                    cubes[col].pop()
                    cubes[col].pop()
                    self.delete_list = [[], []]

                    # 交换活动方块的颜色，再执行一次计算
                    cubes[col].append(Cube(len(cubes[col]), col, active_cubes[1].color))
                    cubes[col].append(Cube(len(cubes[col]) + 1, col, active_cubes[0].color))
                    self.cube_decide()
                    score = - score_distribution[col] * 2
                    for (c, r) in self.delete_list[0]:
                        score += score_distribution[c]
                    score += 20 * len(self.delete_list[1])
                    score_predict[(col, 1)] = score
                    cubes[col].pop()
                    cubes[col].pop()
                    self.delete_list = [[], []]

                # 如果该列处于活动方块当前位置以上，则无法到达；若活动方块在它的左侧，则它的右侧都无法到达，反之亦然
                else:
                    if col < now_col:
                        for i in range(col + 1):
                            score_predict[(i, 0)] = -50
                            score_predict[(i, 1)] = -50
                    else:
                        for i in range(col, 7):
                            score_predict[(i, 0)] = -50
                            score_predict[(i, 1)] = -50

        return score_predict

    # 根据指令和当前方块位置，生成具体的操作命令
    def order_generate(self, operation, col):
        target_col = operation[0]
        order = []
        if target_col < col:
            for i in range(col - target_col):
                order.append('l')
        elif target_col > col:
            for i in range(target_col - col):
                order.append('r')
        if operation[1] == 1:
            order.append('s')
        return order

    # AI移动判定函数
    def ai_thinking(self):
        # 当活动方块处于起始位置或当前位置已低于目标位置时，重新计算
        if self.active_cubes[0].row == GRID_HEIGHT or len(self.cubes[self.auto_target]) >= self.active_cubes[0].row:
            now_row = self.active_cubes[0].row
            score_predict = self.ai_decide(now_row, self.active_cubes[0].col)  # 计算不同操作的价值
            score_ordered = sorted(score_predict.items(), key=lambda x:x[1], reverse=True)  # 根据价值大小排序

            # 简单电脑，在前三价值的选择中按一定概率分布选择
            if self.ai_type == 1:
                p = random.random()
                if p < 0.4 or len(score_ordered) <= 1:
                    operation_basic = score_ordered[0]
                elif p < 0.7 or len(score_ordered) <= 2:
                    operation_basic = score_ordered[1]
                elif p < 0.9 or len(score_ordered) <= 3:
                    operation_basic = score_ordered[2]
                else:
                    operation_basic = score_ordered[3]

            # 普通电脑，在前三价值的选择中按一定概率分布选择，较简单电脑更倾向于更好的价值选择
            elif self.ai_type == 2:
                p = random.random()
                if p < 0.6 or len(score_ordered) <= 1:
                    operation_basic = score_ordered[0]
                elif p < 0.9 or len(score_ordered) <= 2:
                    operation_basic = score_ordered[1]
                else:
                    operation_basic = score_ordered[2]

            # 困难电脑，必然选择最优价值选择
            elif self.ai_type == 3:
                operation_basic = score_ordered[0]

            # 将与选定的价值选择分值相同的操作列入候选
            candidates = []
            for this_operation in score_ordered:
                if this_operation[1] == operation_basic[1]:
                    candidates.append(this_operation[0])
                elif this_operation[1] < operation_basic[1]:
                    break

            # 随机选择其中一个作为选定的选择，并转换为目标位置和操作指令
            operation = random.choice(candidates)
            self.auto_target = operation[0]
            self.auto_order = self.order_generate(operation, self.active_cubes[0].col)

        # 若操作指令列表已清空，则进行速降；否则按照一定的帧间隔调取其中一个操作
        if len(self.auto_order) == 0:
            self.speed = 0.3
        else:
            self.speed = self.basic_speed
            self.ai_count += 1
            if self.ai_count == self.ai_speed:
                if self.auto_order[0] == 'l':
                    self.move_left()
                elif self.auto_order[0] == 'r':
                    self.move_right()
                elif self.auto_order[0] == 's':
                    self.change()
                self.auto_order.pop(0)
                self.ai_count = 0

# 主游戏窗口，按BoxLayout排列
class GameScreen(BoxLayout):

    # com_board:电脑玩家游戏窗口；com_sidebar:电脑玩家边栏；board:人类玩家游戏窗口；sidebar:人类玩家边栏
    com_board = ObjectProperty(None)
    com_sidebar = ObjectProperty(None)
    board = ObjectProperty(None)
    sidebar = ObjectProperty(None)

    # 初始化，生成游戏状态等信息
    def __init__(self, **kwargs):
        super(GameScreen, self).__init__(**kwargs)
        self.com_game_state = GameState(0)
        self.com_board.set_game_state(self.com_game_state)
        self.com_sidebar.set_game_state(self.com_game_state)
        self.game_state = GameState(1)
        self.board.set_game_state(self.game_state)
        self.sidebar.set_game_state(self.game_state)
        self.player_score = self.game_state.score  # 人类玩家得分，作为攻防按键状态依据
        self.bind(pos=self.redraw)
        self.bind(size=self.redraw)
        self.start_game(1)  # 延迟1秒，开始游戏
        self.frame_time = 0  # 每帧时间
        self.last_frame_time = time.time()  # 上一帧时间

    # 开始游戏
    def start_game(self, wait_time):
        global bgm_status
        bgm_status = True
        audio_play_s(confirm_audio)
        Clock.unschedule(self.tick)
        self.com_game_state.reset()
        self.game_state.reset()
        Clock.schedule_once(self.tick, wait_time)

    # 游戏进行函数，当游戏处在进行状态，持续调用函数
    def tick(self, *args):
        # 游戏开始后，进入'auto_move'状态
        if self.com_game_state.game_status == 'start':
            self.com_game_state.game_status = 'auto_move'
            self.game_state.game_status = 'auto_move'

        # 若任意一方进入游戏结束状态，则另一方也进入游戏结束状态，否则更新player_score
        if self.game_state.game_status == 'game_over':
            self.com_game_state.game_status = 'game_over'
        elif self.com_game_state.game_status == 'game_over':
            self.game_state.game_status = 'game_over'
        else:
            self.player_score = self.game_state.score

        # 根据不同游戏状态，执行不同动作；电脑玩家在'active'下额外执行AI移动判定
        if self.com_game_state.game_status == 'active':
            self.com_game_state.ai_thinking()
            self.com_game_state.move_down()
        elif self.com_game_state.game_status == 'auto_move':
            self.com_game_state.auto_move()
        elif self.com_game_state.game_status == 'blink':
            self.com_game_state.blink_process()
        elif self.com_game_state.game_status == 'attack' or self.com_game_state.game_status == 'defend':
            if time.time() - self.com_game_state.action_time > 1:
                self.com_game_state.game_status = 'auto_move'
        if self.game_state.game_status == 'active':
            self.game_state.move_down()
        elif self.game_state.game_status == 'auto_move':
            self.game_state.auto_move()
        elif self.game_state.game_status == 'blink':
            self.game_state.blink_process()
        elif self.game_state.game_status == 'attack' or self.game_state.game_status == 'defend':
            if time.time() - self.game_state.action_time > 1:
                self.game_state.game_status = 'auto_move'

        # 重新绘制游戏画面
        self.redraw()

        now_time = time.time()
        # 若游戏结束，进入暂停状态
        if self.game_state.game_status == 'game_over':
            self.parent.pause()

        # 若未结束，则根据每帧时间，补齐到20毫秒进行下一帧，在性能充足时保持画面稳定
        else:
            self.frame_time = now_time - self.last_frame_time
            if self.frame_time < 0.02:
                delay_time = 0.02 - self.frame_time
                Clock.schedule_once(self.tick, delay_time)
            else:
                Clock.schedule_once(self.tick, 0)
        self.last_frame_time = now_time

    # 重新绘制游戏
    def redraw(self, *args):
        # 若游戏未结束，AI分析是否需要攻击或防御
        if self.com_game_state.game_status != 'game_over':
            self.ai_action_thinking()

        # 更新所有界面
        self.sidebar.refresh()
        self.board.redraw()
        self.com_sidebar.refresh()
        self.com_board.redraw()

    # 游戏暂停，取消游戏进行的队列
    def game_pause(self, *args):
        Clock.unschedule(self.tick)

    # 游戏继续，0.5秒后继续进行游戏
    def game_resume(self, *args):
        Clock.schedule_once(self.tick, 0.5)
        audio_play_s(continue_audio)

    # 计算游戏窗口大小
    def calculate_board_size(self, board):
        # 先以board对象的高度计算游戏窗口高度，使其等于20乘以最大行数的整数倍，再推算出宽度大小
        height = board.height - dp(20)
        height -= height % (20 * GRID_HEIGHT)
        width = height * GRID_WIDTH / GRID_HEIGHT

        # 若得到的宽度大于board对象的总宽，则以宽度作为限制
        if width > board.width:
            width = board.width - dp(20)
            height = width * GRID_HEIGHT / GRID_WIDTH
            height -= height % (20 * GRID_HEIGHT)
            width = height * GRID_WIDTH / GRID_HEIGHT

        # 得到游戏窗口的左下角坐标
        x = board.x + (board.width - width) / 2
        y = (board.height - height) / 2

        return x, y, width, height

    # 计算方块大小
    def block_size(self):
        board_x, board_y, board_width, board_height = \
            self.calculate_board_size(self.board)
        block_width = board_width / GRID_WIDTH
        block_height = board_height / GRID_HEIGHT
        return block_width, block_height

    # 人类玩家攻击函数
    def attack(self):
        if self.game_state.score >= 100:
            self.com_board.attack(int(self.game_state.score // 100))
            self.game_state.score = 0

    # 人类玩家防御函数
    def defend(self):
        self.board.defend()

    # AI玩家攻击函数
    def ai_attack(self):
        if self.com_game_state.score >= 100:
            self.board.attack(int(self.com_game_state.score // 100))
            self.com_game_state.score = 0

    # AI玩家防御函数
    def ai_defend(self):
        self.com_board.defend()

    # AI玩家攻击、防御判定
    def ai_action_thinking(self):
        # 只有AI分数大于等于100时进行判定
        if self.com_game_state.score >= 100:
            # 计算攻防系数，攻击系数为对方底端中央行数+我方分数可攻击的行数，防御系数为我方升起行数+底端中央行数
            now_time = time.time()
            # 仅对方在'active'状态下才进行攻击，避免出现不可控意外被翻盘
            if self.game_state.game_status == 'active':
                attack_index = len(self.game_state.cubes[3]) + int(self.com_game_state.score // 100)
            else:
                attack_index = -1

            # 若防御系数达到10，则进行防御；但若正处在被攻击状态，则延迟0.5秒进行行动，方便人类玩家观察
            defend_index = self.com_game_state.new_line + len(self.com_game_state.cubes[3])
            if defend_index >= 10:
                if self.com_game_state.game_status == 'attack':
                    if now_time - self.com_game_state.action_time > 0.5:
                        self.ai_defend()
                elif self.com_game_state.game_status == 'active':
                    self.ai_defend()

            # 若无需防御且攻击系数更高，则判断是否需要攻击
            elif attack_index >= defend_index:
                # 简单电脑攻击倾向低，攻击判定的间隔长；普通电脑攻击倾向中等，攻击判定间隔中等；困难电脑倾向于积攒点数进行攻击，攻击判定间隔短
                if self.com_game_state.ai_type == 1:
                    if now_time - self.com_game_state.action_decide_time > 5:
                         p = random.random()
                         if p < (attack_index - 5) / 40:
                             self.ai_attack()
                             self.com_game_state.action_decide_time = now_time + 10
                         else:
                             self.com_game_state.action_decide_time = now_time
                elif self.com_game_state.ai_type == 2:
                    if now_time - self.com_game_state.action_decide_time > 3:
                         p = random.random()
                         if p < (attack_index - 5) / 10:
                             self.ai_attack()
                             self.com_game_state.action_decide_time = now_time + 6
                         else:
                             self.com_game_state.action_decide_time = now_time
                elif self.com_game_state.ai_type == 3 and attack_index >= 10:
                    if now_time - self.com_game_state.action_decide_time > 1:
                        self.ai_attack()
                        self.com_game_state.action_decide_time = now_time

# 游戏窗口所在的Board类
class Board(Widget):
    def __init__(self, **kwargs):
        super(Board, self).__init__(**kwargs)
        self.cols = GRID_WIDTH
        self.rows = GRID_HEIGHT
        self.board_information = None
        self.bind(size=self.redraw)
        self.game_state = None

    # 获得游戏状态信息
    def set_game_state(self, game_state):
        self.game_state = game_state

    # 重新绘制
    def redraw(self, *args):
        # board_information为游戏窗口的位置、大小等信息；在初始状态或不稳定状态下重新计算
        if self.board_information is None or self.board_information[3] <= Window.height - 100 or self.board_information[4] <= 0:
            board_x, board_y, board_width, board_height = self.parent.calculate_board_size(self)
            block_width, block_height = self.parent.block_size()
            self.board_information = (board_x, board_y, board_width, board_height, block_width, block_height)

        alpha = 1  # 透明度

        # 绘制canvas.before层，包含游戏窗口底色和活动方块
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.1, 0.1, 0.1, alpha)
            Rectangle(pos=(self.board_information[0], self.board_information[1]),
                      size=(self.board_information[2], self.board_information[3]))

            # 仅在'active'或'game_over'状态绘制活动方块
            if self.game_state.game_status == 'active' or self.game_state.game_status == 'game_over':
                if self.game_state.win:
                    col = self.game_state.active_cubes[0].col
                    Color(0.3, 0.3, 0.3, 0.5 * alpha)
                    Rectangle(pos=(self.board_information[0] + col * self.board_information[4],
                                   self.board_information[1]),
                      size=(self.board_information[4], self.board_information[3]))
                    for cube in self.game_state.active_cubes:
                        self.draw_cube(cube, self.board_information, alpha)

        # 在'auto_move'状态或'blink'状态下，更新canvas层，即底端方块
        if self.game_state.game_status == 'auto_move' or self.game_state.game_status == 'blink':
            self.canvas.clear()
            with self.canvas:
                # 底端方块绘制，当状态是'blink'时，若是需消除的方块，根据游戏blink的值决定是否显示，实现闪烁
                for col, this_col in enumerate(self.game_state.cubes):
                    for row, this_cube in enumerate(this_col):
                        if this_cube.row >= GRID_HEIGHT:
                            continue
                        if self.game_state.game_status == 'blink' and self.game_state.blink:
                            if self.game_state.new_line > 0:
                                if (col, row) in self.game_state.delete_list[0] or (col, row) in self.game_state.delete_list[1]:
                                    continue
                            else:
                                if (col, row) in self.game_state.delete_list[0] or (col, row) in self.game_state.delete_list[1] or row < self.game_state.delete_line:
                                    continue
                        self.draw_cube(this_cube, self.board_information, alpha)

        # 重新绘制canvas.after层，包含攻击、防御提示、游戏窗口框和上下遮罩
        self.canvas.after.clear()
        with self.canvas.after:
            # 防御和攻击提示，包括游戏窗口的灰度遮罩及根据动作时间计算的动态颜色条
            if self.game_state.game_status == 'defend':
                Color(0.1, 0.1, 0.1, 0.5)
                Rectangle(pos=(self.board_information[0], self.board_information[1]),
                      size=(self.board_information[2], self.board_information[3]))
                pos_base_x = self.board_information[0]
                pos_base_y = self.board_information[1] + self.board_information[3]
                pos_base_y -= (self.board_information[3] / 2 + dp(15)) * (time.time() - self.game_state.action_time) * 2
                Color(0, 0.8, 0, 1)
                Rectangle(pos=(pos_base_x, pos_base_y), size=(self.board_information[2], dp(30)))
            elif self.game_state.game_status == 'attack':
                Color(0.1, 0.1, 0.1, 0.5)
                Rectangle(pos=(self.board_information[0], self.board_information[1]),
                      size=(self.board_information[2], self.board_information[3]))
                pos_base_x = self.board_information[0]
                pos_base_y = self.board_information[1]
                pos_base_y += (self.board_information[3] / 2 - dp(15)) * (time.time() - self.game_state.action_time) * 2
                Color(0.8, 0, 0, 1)
                Rectangle(pos=(pos_base_x, pos_base_y), size=(self.board_information[2], dp(30)))

            # 游戏上下的遮罩，遮盖超出游戏窗口范围的方块
            Color(0.2, 0.2, 0.2, 1)
            Rectangle(pos=(self.board_information[0], self.board_information[1] + self.board_information[3] + dp(2)),
                      size=(self.board_information[2], self.parent.height - self.board_information[3]))
            Color(0.2, 0.2, 0.2, 1)
            Rectangle(pos=(self.board_information[0], 0),
                      size=(self.board_information[2], self.board_information[1]))

            # 游戏窗口外框线
            Color(0.5, 0.5, 0.5, 1)
            Line(width=2., rectangle=(self.board_information[0] - dp(2), self.board_information[1] - dp(2),
                                      self.board_information[2] + dp(4), self.board_information[3] + dp(4)))

    # 方块绘制函数
    def draw_cube(self, cube, board_information, alpha):
        board_x, board_y, board_width, board_height, block_width, block_height = board_information

        # 方块的灰色边框
        Color(0.8, 0.8, 0.8, alpha)
        Rectangle(pos=(board_x + cube.col * block_width,
                     board_y + cube.row * block_height),
                  size=(block_width, block_height))

        # 获取cube的颜色
        if cube.color >= 0:
            color = (all_color_list[0][cube.color][0], all_color_list[0][cube.color][1],
                     all_color_list[0][cube.color][2], alpha)
        else:
            color = (all_color_list[1][0], all_color_list[1][1], all_color_list[1][2], alpha)

        # 绘制方块的主色
        Color(*color)
        Rectangle(pos=(board_x + cube.col * block_width + block_width * 0.05,
                     board_y + cube.row * block_height + block_height * 0.05),
                  size=(block_width * 0.9, block_height * 0.9))

    # 攻击函数，增加new_line，进入'attack'状态
    def attack(self, line):
        audio_play_s(attack_audio)
        self.game_state.new_line += line
        self.game_state.game_status = 'attack'
        self.game_state.action_time = time.time()
        self.game_state.action = True

    # 防御函数，增加delete_line，进入'defend'状态
    def defend(self):
        if self.game_state.score >= 100:
            audio_play_s(defend_audio)
            delete_line = int(self.game_state.score // 100)
            self.game_state.delete_line += delete_line
            self.game_state.game_status = 'defend'
            self.game_state.action_time = time.time()
            self.game_state.score = 0
            self.game_state.action = True

    # 检测触摸操作
    def on_touch_down(self, touch):
        # 仅人类玩家有效
        if self.game_state.type == 0:
            return

        # 当处在'active'状态且触摸位置位置游戏窗口内时，记录按下的位置，并还原掉落速度
        if self.game_state.game_status == 'active' and self.board_information[0] < touch.x < self.board_information[0] + self.board_information[2]:
            touch.ud['start_pos'] = (touch.x, touch.y)
            touch.ud['move_pos'] = (touch.x, touch.y)
            touch.ud['move'] = False
            self.game_state.speed = self.game_state.basic_speed

    # 检测触摸位移
    def on_touch_move(self, touch):
        # 仅人类玩家有效
        if self.game_state.type == 0:
            return

        # 当处在'active'状态且已记录按下位置时，在向下移动幅度较小且左右移动足够时，执行左、右移动活动方块操作
        if self.game_state.game_status == 'active' and 'start_pos' in touch.ud:
            if touch.y - touch.ud['start_pos'][1] >= -self.board_information[5] * 2:
                if touch.x - touch.ud['move_pos'][0] > self.board_information[4] * 3 / 4:
                    self.game_state.move_right()
                    touch.ud['move'] = True
                    touch.ud['move_pos'] = (touch.x, touch.y)
                elif touch.x - touch.ud['move_pos'][0] < -self.board_information[4] * 3 / 4:
                    self.game_state.move_left()
                    touch.ud['move'] = True
                    touch.ud['move_pos'] = (touch.x, touch.y)

    # 检测触摸结束
    def on_touch_up(self, touch):
        # 仅人类玩家有效
        if self.game_state.type == 0:
            return

        # 当处在'active'状态且已记录按下位置时，判断是否向下移动较大幅度，若是，则速降
        if self.game_state.game_status == 'active' and 'start_pos' in touch.ud:
            if touch.y - touch.ud['start_pos'][1] < -self.board_information[5] * 2:
                self.game_state.speed = 0.3

            # 若不速降且未发生左右移动，则执行颜色交换
            elif not touch.ud['move']:
                self.game_state.change()

# 游戏边栏类，记录游戏信息
class Sidebar(BoxLayout):

    # 游戏玩家名、分数、下一个方块、功能按键
    name = ObjectProperty(None)
    score = ObjectProperty(None)
    next_cube = ObjectProperty(None)
    function_button = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(Sidebar, self).__init__(**kwargs)
        self.bind(size=self.refresh)
        self.game_state = None
        self.size_reset = False

    # 获取游戏状态，若为AI玩家，得到其难度类型
    def set_game_state(self, game_state):
        self.game_state = game_state
        if self.game_state.type == 0:
            if self.game_state.ai_type == 1:
                self.name.text = 'EASY'
            elif self.game_state.ai_type == 2:
                self.name.text = 'NORM'
            elif self.game_state.ai_type == 3:
                self.name.text = 'HARD'

    # 重新绘制游戏信息
    def refresh(self, *args):
        # 若画布尺寸更新未完成，则重新计算功能按键位置
        if self.parent.block_size()[0] <= 0:
            # 当sidebar宽度大于高度的1/8时，以高度的1/8限制功能按键的宽度
            if self.width > self.height / 8:
                self.function_button.pos = (self.pos[0] + (self.width - self.height / 8) / 2, self.pos[1])
                self.function_button.size = (self.height / 8, self.height / 8)
            else:
                self.function_button.pos = self.pos
                self.function_button.size = (self.width, self.height / 8)

        # 获取游戏得分
        self.score.text = str(self.game_state.score)
        if self.game_state.score >= 999:
            self.score.color = (1, 0, 0, 1)
        elif self.game_state.score >= 100:
            self.score.color = (1, 1, 0, 1)
        else:
            self.score.color = (1, 1, 1, 1)

        # 若游戏结束或处在刚开始的状态，功能按键不可用
        if self.game_state.game_status == 'game_over' or self.game_state.game_status == 'start':
            if not self.function_button.disabled:
                self.function_button.disabled = True
                self.function_button.redraw()
        else:
            # 当游戏处于'blink'状态且存在得分时，绘制基本得分、bonus得分和chain得分信息
            if self.game_state.game_status == 'blink' and self.game_state.round_score > 0:
                if self.game_state.basic_score > 0:
                    self.basic_score.text = '+' + str(self.game_state.basic_score)
                else:
                    self.basic_score.text = ''
                if self.game_state.bonus_score > 0:
                    self.bonus_score.text = '+' + str(self.game_state.bonus_score) + ' BO'
                else:
                    self.bonus_score.text = ''
                if self.game_state.chain_score > 0:
                    self.chain_score.text = '+' + str(self.game_state.chain_score) + ' CH'
                else:
                    self.chain_score.text = ''
            else:
                self.basic_score.text = ''
                self.bonus_score.text = ''
                self.chain_score.text = ''

            # 当玩家分数大于等于100时，使功能按键可用，否则禁用
            if self.parent.player_score >= 100:
                if self.function_button.disabled:
                    self.function_button.disabled = False
                    self.function_button.redraw()
            else:
                if not self.function_button.disabled:
                    self.function_button.disabled = True
                    self.function_button.redraw()

            self.render_next_cube()  # 绘制下一个方块

    # 绘制下一个方块函数
    def render_next_cube(self):
        # 根据下一个方块的颜色信息，绘出下一个方块提示
        self.next_cube.canvas.before.clear()
        self.next_cube.canvas.clear()
        cube_width, cube_height = self.parent.block_size()
        x = self.next_cube.x + (self.next_cube.size[0] - cube_width) / 2
        y = self.next_cube.y + (self.next_cube.size[1] - cube_height * 2) / 2

        with self.next_cube.canvas:
            Color(0.8, 0.8, 0.8, 1)
            Rectangle(pos=(x, y),
                      size=(cube_width, cube_height))
            Color(*all_color_list[0][self.game_state.next_color[0]])
            Rectangle(pos=(x + cube_width * 0.05, y + cube_height * 0.05),
                      size=(cube_width * 0.9, cube_height * 0.9))

            Color(0.8, 0.8, 0.8, 1)
            Rectangle(pos=(x, y + cube_height),
                      size=(cube_width, cube_height))
            Color(*all_color_list[0][self.game_state.next_color[1]])
            Rectangle(pos=(x + cube_width * 0.05, y + cube_height + cube_height * 0.05),
                      size=(cube_width * 0.9, cube_height * 0.9))

# 游戏页面管理器
class CubeScreen(ScreenManager):

    # 初始化，进入标题页面
    def __init__(self, *args, **kwargs):
        super(CubeScreen, self).__init__(**kwargs)
        self.title_screen = TitleScreen()
        self.add_widget(self.title_screen)

    # 开始游戏函数，确定AI强度、各组件的屏幕占比，并切换游戏页面
    def start_game(self, type):
        global ai_type
        board_ratio = (self.height * GRID_WIDTH / GRID_HEIGHT) / self.width
        sidebar_ratio = (self.height / 10) / self.width
        if sidebar_ratio + board_ratio > 0.5:
            sidebar_ratio = (1 - 2 * board_ratio) / 2

        CubeApp.RATIO[0] = board_ratio
        CubeApp.RATIO[1] = sidebar_ratio
        ai_type = type

        if self.has_screen('vscom'):
            self.remove_widget(self.get_screen('vscom'))
            del self.main_screen

        # 生成主游戏界面，切换界面
        self.main_screen = MainScreen()
        self.add_widget(self.main_screen)
        self.transition.direction = 'left'
        self.current = 'vscom'

    # 回到标题界面
    def title(self):
        if self.has_screen('vscom'):
            self.remove_widget(self.get_screen('vscom'))
        self.title_screen = TitleScreen()
        self.add_widget(self.title_screen)
        self.transition.direction = 'right'
        self.current = 'title'

    # 退出函数，若处于主游戏界面则暂停，若处于标题界面则直接退出
    def back(self):
        if self.current == 'vscom':
            self.main_screen.pause()
        else:
            App.get_running_app().stop()

# 标题页面类
class TitleScreen(Screen):
    title_box = ObjectProperty(None)

# 主游戏界面类
class MainScreen(Screen):

    def __init__(self, *args, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.game = GameScreen()
        self.add_widget(self.game)
        self.pause_state = False

    # 游戏暂停函数
    def pause(self, *args):
        if not self.pause_state:
            global bgm_status
            self.game.game_pause()
            # 生成一个menu_back_layout布局，叠加在主布局上形成遮罩，并在其中央生成一个菜单布局
            self.menu_back_layout = AnchorLayout(opacity=1, anchor_x='center', size=Window.size)
            menu_layout = BoxLayout(size_hint=(0.15, 0.4), spacing=dp(10),
                                    orientation='vertical', size=(0.24 * Window.size[0], 0.44 * Window.size[1]),
                                    pos=(0.38 * Window.size[0], 0.28 * Window.size[1]))
            with self.menu_back_layout.canvas:
                Color(0, 0, 0, 0.3)
                Rectangle(pos=self.menu_back_layout.pos,
                          size=self.menu_back_layout.size)
            with menu_layout.canvas:
                Color(0.9, 0.9, 0.9, 1)
                RoundedRectangle(pos=menu_layout.pos,
                          size=menu_layout.size, corner_radius=dp(5))

            # 根据游戏胜利、失败或暂停绘制不同的Label文字
            if not self.game.game_state.win:
                menu_label = Label(text='You Lose!', bold=True, color=(0, 0, 0, 1))
                bgm_status = False
                audio_play_s(fail_audio)
            elif not self.game.com_game_state.win:
                menu_label = Label(text='You Win!', bold=True, color=(0, 0, 0, 1))
                bgm_status = False
                audio_play_s(victory_audio)
            else:
                menu_label = Label(text='PAUSE', bold=True, color=(0, 0, 0, 1))
                audio_play_s(pause_audio)

            # 继续、重新进行游戏、回到标题、退出按键
            resume_button = RoundedButton(text='RESUME', bold=True, on_press=self.resume, back_color=(0, 0, 0.8, 1), radius=dp(5))
            restart_button = RoundedButton(text='RESTART', bold=True, on_press=self.restart, back_color=(0, 0, 0.8, 1), radius=dp(5))
            title_button = RoundedButton(text='TITLE', bold=True, on_press=self.title, back_color=(0, 0, 0.8, 1), radius=dp(5))
            exit_button = RoundedButton(text='EXIT', bold=True, on_press=self.exit_game, back_color=(0, 0, 0.8, 1), radius=dp(5))

            # 若游戏结束，则继续游戏按键不可用
            if self.game.game_state.game_status == 'game_over':
                resume_button.disabled = True
            else:
                resume_button.disabled = False

            menu_layout.add_widget(menu_label)
            menu_layout.add_widget(resume_button)
            menu_layout.add_widget(restart_button)
            menu_layout.add_widget(title_button)
            menu_layout.add_widget(exit_button)
            self.menu_back_layout.add_widget(menu_layout)
            self.add_widget(self.menu_back_layout)
            self.pause_state = True

    # 退出游戏，退出App
    def exit_game(self, *args):
        App.get_running_app().stop()

    # 回到标题
    def title(self, *args):
        self.parent.title()
        audio_play_s(confirm_audio)
        global bgm_status
        bgm_status = False

    # 继续游戏
    def resume(self, *args):
        self.pause_state = False
        self.remove_widget(self.menu_back_layout)
        self.game.game_resume()

    # 重开一局游戏
    def restart(self, *args):
        self.pause_state = False
        self.remove_widget(self.menu_back_layout)
        self.parent.start_game(ai_type)

# 主App类
class CubeApp(App):
    screen = ObjectProperty(None)
    RATIO = [0.4, 0.2]

    def build(self):
        self.screen = CubeScreen()
        self.bind(on_start=self.post_build_init)
        return self.screen

    # 监控按键操作
    def post_build_init(self, *args):
        Window.bind(on_keyboard=self.my_key_handler)

    # 若按返回键，则调用back函数
    def my_key_handler(self, window, keycode1, keycode2, text, modifiers):
        if keycode1 in [27, 1001]:
            self.screen.back()
            return True
        return False

if __name__ == '__main__':
    CubeApp().run()