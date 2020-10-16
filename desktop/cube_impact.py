import pygame
import random
import time
import os
from threading import Thread
import simpleaudio as sa
import sys

# 获取绝对路径，避免打包后出现错误
def getPath(fileName):
    path = os.path.join(os.path.dirname(sys.argv[0]), fileName)
    return path

# 音频、字体文件的路径
move_audio = getPath('resources/audio/move.wav')  # 左右移动
change_audio = getPath('resources/audio/rotate.wav')  # 交换颜色
drop_audio = getPath('resources/audio/collapse.wav')  # 方块落地
destroy_audio = getPath('resources/audio/medal.wav')  # 普通消除
special_audio = getPath('resources/audio/gem.wav')  # 银色方块消除
attack_audio = getPath('resources/audio/attack.wav')  # 攻击
defend_audio = getPath('resources/audio/erase1.wav')  # 防御
victory_audio = getPath('resources/audio/excellent.wav')  # 获胜
fail_audio = getPath('resources/audio/fail.wav')  # 失败
pause_audio = getPath('resources/audio/pause.wav')  # 暂停
continue_audio = getPath('resources/audio/b2b_continue.wav')  # 继续、选择
confirm_audio = getPath('resources/audio/b2b_start.wav')  # 确定
bgm_audio = getPath('resources/audio/bgm.mp3')  # 背景音乐（取自Nihon Falcomポムっと，待替换为原创音乐）
font_path = getPath('resources/fonts/arial.ttf')  # 使用字体

pygame.init()
win = pygame.display.set_mode((600, 360))  # 画布窗口的大小
pygame.display.set_caption("方块碰 by emhang")  # 窗口标题

bgm_status = False  # 背景音乐状态通过全局变量控制

# 背景音乐播放函数
def bgm_play():
    pygame.mixer.init(frequency=16000)
    pygame.mixer.music.load(bgm_audio)
    pygame.mixer.music.set_volume(0.5)
    while True:
        if not pygame.mixer.music.get_busy() and bgm_status:
            pygame.mixer.music.play(-1)
        elif pygame.mixer.music.get_busy() and not bgm_status:
            pygame.mixer.music.fadeout(500)

# 通过子线程控制背景音乐播放
bgm_thread = Thread(target=bgm_play)
bgm_thread.setDaemon(True)
bgm_thread.start()

# 音效播放函数，使用simpleaudio实现多音效同时播放
def audio_play(path):
    wave_obj = sa.WaveObject.from_wave_file(path)
    play_obj = wave_obj.play()
    play_obj.wait_done()

# 音效播放子线程化
def thread_audio_play(path):
    t = Thread(target=audio_play, args=(path,))
    t.setDaemon(True)
    t.start()

# 绘制方块
def draw_cube(x, y, width, height, color):
    x = int(x)
    y = int(y)
    pygame.draw.rect(win, (150, 150, 150), (x, y, width, height))
    pygame.draw.rect(win, color, (x + 2, y + 2, width - 4, height - 4))

# 绘制文本
def draw_text(content, size, color, pos, bg=None):
    pygame.font.init()
    font = pygame.font.Font(font_path, size)
    text = font.render(content, True, color, bg)
    win.blit(text, pos)

# 方块类，定义单个方块的行为
class Cube:
    # 方块的宽与高
    WIDTH = 30
    HEIGHT = 30

    # 初始化游戏基本位置、行、列、颜色及位置信息
    def __init__(self, game_position, row, col, color = -1):
        self.row = row
        self.col = col
        self.color = color
        self.game_position = game_position
        self.x = self.col * Cube.WIDTH + self.game_position
        self.y = 360 - ((self.row + 1) * Cube.HEIGHT)

    # 左右移动判定
    def col_change(self, bias):
        self.col += bias
        if self.col > 6:
            self.col = 6
            return False
        elif self.col < 0:
            self.col = 0
            return False
        self.x = self.col * Cube.WIDTH + self.game_position
        return True

    # 向下移动判定，当y坐标移动到跨越行的界限时改变row值
    def row_change(self, speed):
        self.y += speed
        if self.y - (360 - ((self.row + 1) * Cube.HEIGHT)) >= Cube.HEIGHT:
            self.row -= 1
            self.y = 360 - ((self.row + 1) * Cube.HEIGHT)
        elif (360 - ((self.row + 1) * Cube.HEIGHT)) - self.y >= Cube.HEIGHT:
            self.row += 1
            self.y = 360 - ((self.row + 1) * Cube.HEIGHT)

# 游戏类，定义单个游戏的状态
class Game:
    # 可选颜色列表，包括普通方块颜色和特殊方块颜色
    all_color_list = (((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255)), (200, 200, 200))

    # 初始化，可接受游戏位置、游戏进行难度、键盘风格、游戏者名字、AI类型等参数
    def __init__(self, game_position, hard_choice, key_style, player_name, ai_type=1):
        self.player_name = player_name
        self.game_position = game_position
        # 游戏进行难度，决定使用多少种方块颜色及基础掉落速度等
        self.hard_choice = hard_choice
        if self.hard_choice == 1:
            self.basic_speed = 0.5
            self.color_list = self.all_color_list[0][0:4]
        elif hard_choice == 2:
            self.basic_speed = 1
            self.color_list = self.all_color_list[0][0:4]
        elif hard_choice == 3:
            self.basic_speed = 1
            self.color_list = self.all_color_list[0][0:5]

        self.color_mode = 1  # 颜色模式，1代表存在特殊方块
        self.silver_odds = 0.04  # 特殊方块的生成几率
        self.delete_list = [[], []]  # 待消除方块的坐标，包含普通方块和特殊方块
        self.delete_line = 0  # 由于防御行为待消除的行数
        self.new_line = 0  # 由于攻击行为待升起的行数
        self.win = True  # 游戏获胜boolean，败者为False
        self.status = 'automove'  # 游戏状态，开局时为'automove'状态
        self.blink = True  # 闪烁状态，在消除闪烁时切换
        self.blink_count = 0  # 闪烁计数，控制闪烁的进程
        # 生成活动方块和下一组活动方块的颜色
        self.active_cubes = (Cube(self.game_position, 12, 3, random.randint(0, len(self.color_list) - 1)),
                             Cube(self.game_position, 13, 3, random.randint(0, len(self.color_list) - 1)))
        self.next_color = (random.randint(0, len(self.color_list) - 1),
                           random.randint(0, len(self.color_list) - 1))

        self.speed = self.basic_speed  # 方块的实际掉落速度
        self.score = 0  # 游戏得分
        self.round = 0  # 游戏得分的轮次
        self.round_score = 0  # 每轮次的得分
        self.add_score = 0  # 已经加上的得分，在'blink'状态时逐渐将round_score的分数加到score中
        self.basic_score = 0  # 基础得分，消除1个方块=1分
        self.bonus_score = 0  # bonus得分，每轮消除超过3个方块的额外得分，以及特殊方块的额外分数
        self.chain_score = 0  # chain得分，每多一个消除轮次增加得分
        self.cubes = [[], [], [], [], [], [], []]  # 游戏下方的方块列表
        # 随机生成3行方块作为初始方块
        new_cubes = self.generate_cube(3)
        self.cubes = new_cubes

        # 键盘风格，为0代表是AI控制，1为第一组控制按键，2为第二组控制按键
        self.key_style = key_style
        if key_style == 0:
            # AI控制时，设定自动指令序列、目标位置、攻击判定时间、AI行动间隔等信息
            self.auto_order = []
            self.auto_target = 3
            self.action_decide_time = time.time()
            self.ai_type = ai_type
            self.ai_count = 0

            # 根据不同的AI类型，设定每两次操作的行为间隔
            if ai_type == 1:
                self.ai_speed = 50
            elif ai_type == 2:
                self.ai_speed = 25
            elif ai_type == 3:
                self.ai_speed = 12

        # 两种不同的键盘按键列表
        if key_style == 1:
            self.key = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_k, pygame.K_l]
        elif key_style == 2:
            self.key = [pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_1, pygame.K_2]

        self.start_time = time.time()  # 游戏开始的时间
        self.last_time = time.time()  # 最近一次自动升起的时间
        self.pause_time = 0  # 暂停时间，每次暂停时进行计时，每次自动升起后归零
        self.time_interval = 9 - hard_choice  # 自动升起的时间间隔，根据游戏进行难度有所区别
        self.action_start_time = time.time()  # 攻击或防御行为的开始时间

    # 基本游戏信息绘制函数
    def game_information_draw(self):
        # 绘制黑色背景
        pygame.draw.rect(win, (0, 0, 0), (self.game_position - 20, 0, 18, 360))
        pygame.draw.rect(win, (0, 0, 0), (self.game_position + 212, 0, 68, 360))

        # 绘制左右间隔线
        pygame.draw.line(win, (200, 200, 200), (self.game_position - 2, 0), (self.game_position - 2, 360), 2)
        pygame.draw.line(win, (200, 200, 200), (self.game_position + 210, 0), (self.game_position + 210, 360), 2)

        # 绘制游戏得分
        draw_text("SCORE", 15, (255, 255, 255), (self.game_position + 220, 10))
        if self.score >= 999:
            draw_text(str(self.score), 15, (255, 0, 0), (self.game_position + 220, 30))
        elif self.score >= 100:
            draw_text(str(self.score), 15, (255, 255, 0), (self.game_position + 220, 30))
        else:
            draw_text(str(self.score), 15, (255, 255, 255), (self.game_position + 220, 30))

        # 当处在消除状态时，绘制基础得分、bonus得分和chain得分
        if self.basic_score > 0:
            draw_text('+' + str(self.basic_score), 10, (255, 255, 255), (self.game_position + 220, 50))
        if self.bonus_score > 0:
            draw_text('+' + str(self.bonus_score) + ' BO', 10, (255, 255, 0), (self.game_position + 220, 60))
            if self.chain_score > 0:
                draw_text('+' + str(self.chain_score) + ' CHAIN', 10, (255, 150, 0), (self.game_position + 220, 70))
        else:
            if self.chain_score > 0:
                draw_text('+' + str(self.chain_score) + ' CHAIN', 10, (255, 150, 0), (self.game_position + 220, 60))

        # 绘制下一个方块的颜色
        draw_cube(this_game.game_position + 230, 90, Cube.WIDTH, Cube.HEIGHT, this_game.color_list[this_game.next_color[1]])
        draw_cube(this_game.game_position + 230, 120, Cube.WIDTH, Cube.HEIGHT, this_game.color_list[this_game.next_color[0]])

        # 若为AI玩家，绘制其难度；若为人类玩家，绘制键盘控制按键指示
        if self.key_style == 0:
            if self.ai_type == 1:
                draw_text("EASY", 12, (255, 255, 255), (self.game_position + 220, 320))
            elif self.ai_type == 2:
                draw_text("NORMAL", 12, (255, 255, 255), (self.game_position + 220, 320))
            elif self.ai_type == 3:
                draw_text("HARD", 12, (255, 255, 255), (self.game_position + 220, 320))
        else:
            if self.key_style == 1:
                key_name = ['▲', '▼' , '◄', '►', 'K', 'L']
            elif self.key_style == 2:
                key_name = ['W', 'S', 'A', 'D', '1', '2']
            draw_text(key_name[0] + " : Change", 10, (255, 255, 255), (self.game_position + 220, 160))
            draw_text(key_name[1] + " : Drop", 10, (255, 255, 255), (self.game_position + 220, 180))
            draw_text(key_name[2] + " : Left", 10, (255, 255, 255), (self.game_position + 220, 200))
            draw_text(key_name[3] + " : Right", 10, (255, 255, 255), (self.game_position + 220, 220))
            draw_text(key_name[4] + " : Attack", 10, (255, 255, 255), (self.game_position + 220, 240))
            draw_text(key_name[5] + " : Defend", 10, (255, 255, 255), (self.game_position + 220, 260))

        # 绘制游戏者名字
        draw_text(self.player_name, 12, (255, 255, 255), (self.game_position + 220, 340))

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
                    if self.color_mode == 1:
                        p = random.random()
                        if p < self.silver_odds:
                            color = -1
                        else:
                            color = random.randint(0, len(self.color_list) - 1)
                    else:
                        color = random.randint(0, len(self.color_list) - 1)

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
                new_cubes[col].append(Cube(self.game_position, row, col, color))

        # 最后清除一开始加入的cubes最低行方块
        for col in range(7):
            if len(self.cubes[col]) > 0:
                new_cubes[col].pop(0)

        return new_cubes

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

# 游戏进行函数，控制游戏进行的主要过程
def game_run(this_game):
    # game_status为0，表示游戏在进行状态
    if game_status == 0:
        # 'active'状态下，控制活动方块的移动
        if this_game.status == 'active':
            # 绘制活动方块，每帧自动下落speed
            col = this_game.active_cubes[0].col
            pygame.draw.rect(win, (30, 30, 30), (col * Cube.WIDTH + this_game.game_position, 0, Cube.WIDTH, 360))
            this_game.active_cubes[0].row_change(this_game.speed)
            this_game.active_cubes[1].row_change(this_game.speed)

            # 如果下落的位置达到底部方块的位置或画布底端，则判定为接触，此时将活动方块加入底部方块列表，并判定消除、生成新的活动方块
            if this_game.active_cubes[0].row <= len(this_game.cubes[this_game.active_cubes[0].col]):
                this_game.cubes[this_game.active_cubes[0].col].append(
                        Cube(this_game.game_position, this_game.active_cubes[0].row, this_game.active_cubes[0].col, this_game.active_cubes[0].color))
                this_game.cubes[this_game.active_cubes[0].col].append(
                        Cube(this_game.game_position, this_game.active_cubes[1].row, this_game.active_cubes[1].col, this_game.active_cubes[1].color))
                this_game.cube_decide()
                this_game.active_cubes = (
                    Cube(this_game.game_position, 12, 3, this_game.next_color[0]), Cube(this_game.game_position, 13, 3, this_game.next_color[1]))

                # 如果存在需消除的方块，则进行'blink'状态，同时计算得分
                if len(this_game.delete_list[0]) > 0:
                    this_game.blink_count = 0
                    this_game.status = 'blink'
                    this_game.basic_score = len(this_game.delete_list[0])
                    if this_game.basic_score > 3:
                        this_game.bonus_score = this_game.basic_score - 3
                    else:
                        this_game.bonus_score = 0
                    if len(this_game.delete_list[1]) > 0:
                        this_game.bonus_score += len(this_game.delete_list[1]) * 100
                        thread_audio_play(destroy_audio)
                        thread_audio_play(special_audio)
                    else:
                        thread_audio_play(destroy_audio)
                    this_game.round = 1
                    this_game.round_score = this_game.basic_score + this_game.bonus_score
                    this_game.add_score = 0
                # 若不存在需消除的方块，在无防御行为且中间行达到顶部时判定游戏失败，否则回到'automove'状态
                else:
                    if this_game.delete_line == 0 and len(this_game.cubes[3]) >= 12:
                        return False
                    else:
                        thread_audio_play(drop_audio)
                        this_game.status = 'automove'
            # 不存在接触时，绘制活动方块
            else:
                draw_cube(this_game.active_cubes[0].x, this_game.active_cubes[0].y, Cube.WIDTH, Cube.HEIGHT, this_game.color_list[this_game.active_cubes[0].color])
                draw_cube(this_game.active_cubes[1].x, this_game.active_cubes[1].y, Cube.WIDTH, Cube.HEIGHT, this_game.color_list[this_game.active_cubes[1].color])

        # 'automove'状态下，底端方块进行自动移动、归位
        elif this_game.status == 'automove':
            # 判断是否存在方块的row值与实际在列表中的位置不符，若有，则按照3的速度移动，直到相符
            move_cubes = 0
            for col, this_col in enumerate(this_game.cubes):
                for row, this_cube in enumerate(this_col):
                    if this_cube.row > row:
                        this_cube.row_change(3)
                        move_cubes += 1
                    elif this_cube.row < row:
                        this_cube.row_change(-3)
                        move_cubes += 1

            # move_cubes为0，代表全部已经归位，此时进行消除判断
            if move_cubes == 0:
                this_game.cube_decide()
                # 若无可消除的方块，则判断是否需要自动升起
                if len(this_game.delete_list[0]) == 0:
                    # 先判断根据经过的时间是否需要升起
                    time_line = int((now_time - this_game.last_time - this_game.pause_time) // this_game.time_interval)
                    if time_line > 0:
                        this_game.last_time = time.time()
                        this_game.time_interval = random.uniform(6, 8) - this_game.hard_choice
                        this_game.pause_time = 0
                        this_game.new_line += time_line

                    # 若自动升起行数大于0，则生成新的行数加入底端方块列表
                    if this_game.new_line > 0:
                        new_cubes = this_game.generate_cube(this_game.new_line)
                        for col in range(7):
                            this_game.cubes[col] = new_cubes[col] + this_game.cubes[col]
                        this_game.new_line = 0

                    # 否则判断是否有防御行为，若无，则回到'active'状态；若有，进入'blink'状态
                    else:
                        if this_game.delete_line == 0:
                            this_game.next_color = (random.randint(0, len(this_game.color_list) - 1), random.randint(0, len(this_game.color_list) - 1))
                            this_game.status = 'active'
                            this_game.round = 0
                        else:
                            this_game.blink_count = 0
                            this_game.status = 'blink'
                            thread_audio_play(destroy_audio)
                            this_game.round_score = 0
                            this_game.add_score = 0

                # 若有需要消除的方块，则计算得分、进入'blink'状态
                else:
                    this_game.basic_score = len(this_game.delete_list[0])
                    if this_game.basic_score > 3:
                        this_game.bonus_score = this_game.basic_score - 3
                    else:
                        this_game.bonus_score = 0
                    if len(this_game.delete_list[1]) > 0:
                        this_game.bonus_score += len(this_game.delete_list[1]) * 100
                        thread_audio_play(destroy_audio)
                        thread_audio_play(special_audio)
                    else:
                        thread_audio_play(destroy_audio)
                    if this_game.round < 3:
                        this_game.chain_score = this_game.round * 10
                    else:
                        this_game.chain_score = 30
                    this_game.round += 1
                    this_game.round_score = this_game.basic_score + this_game.bonus_score + this_game.chain_score
                    this_game.add_score = 0
                    this_game.blink_count = 0
                    this_game.status = 'blink'

        # 'blink'为闪烁状态，将需要消除的方块或整行进行闪烁显示，同时将需要增加的分数逐渐加入score中
        elif this_game.status == 'blink':
            # 若本轮消除存在得分，则将得分逐帧逐渐加入score中，增强动态感
            if this_game.round_score > 0:
                add_score = int(this_game.round_score * this_game.blink_count / 30)
                if add_score > this_game.add_score:
                    this_game.score += (add_score - this_game.add_score)
                    if this_game.score > 999:
                        this_game.score = 999
                    this_game.add_score = add_score

            # 每帧进行计数，每5帧切换一次显示状态
            this_game.blink_count += 1
            if this_game.blink_count % 5 == 0:
                this_game.blink = not this_game.blink

            # 达到30帧结束闪烁，补齐未加的分数，将分数数据清空，同时在cubes中删除待消除的方块，回到'automove'状态
            if this_game.blink_count >= 30:
                if this_game.round_score > 0:
                    if this_game.round_score > this_game.add_score:
                        this_game.score += (this_game.round_score - this_game.add_score)
                        if this_game.score > 999:
                            this_game.score = 999
                    this_game.round_score = 0
                    this_game.add_score = 0
                    this_game.basic_score = 0
                    this_game.bonus_score = 0
                    this_game.chain_score = 0
                cubes_ori = this_game.cubes.copy()
                this_game.cubes = [[], [], [], [], [], [], []]
                if this_game.new_line > 0:
                    for col, this_col in enumerate(cubes_ori):
                        for row, this_cube in enumerate(this_col):
                            if (col, row) not in this_game.delete_list[0] and (col, row) not in this_game.delete_list[1]:
                                this_game.cubes[col].append(this_cube)
                else:
                    for col, this_col in enumerate(cubes_ori):
                        for row, this_cube in enumerate(this_col):
                            if (col, row) not in this_game.delete_list[0] and (col, row) not in this_game.delete_list[1] and row >= this_game.delete_line:
                                this_game.cubes[col].append(this_cube)
                    this_game.delete_line = 0
                this_game.status = 'automove'

    # 底端方块绘制，当状态是'blink'时，若是需消除的方块，根据游戏blink的值决定是否显示，实现闪烁
    for col, this_col in enumerate(this_game.cubes):
        for row, this_cube in enumerate(this_col):
            if this_game.status == 'blink':
                if this_game.blink:
                    if this_game.new_line > 0:
                        if (col, row) in this_game.delete_list[0] or (col, row) in this_game.delete_list[1]:
                            continue
                    else:
                        if (col, row) in this_game.delete_list[0] or (col, row) in this_game.delete_list[1] or row < this_game.delete_line:
                            continue
            if this_cube.color >= 0:
                draw_cube(this_cube.x, this_cube.y, Cube.WIDTH, Cube.HEIGHT, this_game.color_list[this_cube.color])
            else:
                # 特殊方块显示，根据special_brightness决定其亮度，实现"呼吸"效果
                color = (int(Game.all_color_list[1][0] * special_brightness), int(Game.all_color_list[1][1] * special_brightness), int(Game.all_color_list[1][2] * special_brightness))
                draw_cube(this_cube.x, this_cube.y, Cube.WIDTH, Cube.HEIGHT, color)

    # 游戏进行时间计算，根据游戏进行时间和游戏进行难度，得出游戏基础速度的值
    game_time = now_time - this_game.start_time - game_pause_time
    if this_game.hard_choice == 1:
        this_game.basic_speed = 0.5 + game_time * 0.01
        if this_game.basic_speed > 3:
            this_game.basic_speed = 3
    elif this_game.hard_choice == 2:
        this_game.basic_speed = 0.8 + game_time * 0.02
        if this_game.basic_speed > 5:
            this_game.basic_speed = 5
    elif this_game.hard_choice == 3:
        this_game.basic_speed = 1 + game_time * 0.03
        if this_game.basic_speed > 5:
            this_game.basic_speed = 5

    # 攻击、防御提示绘制，根据动作时间流逝，动态显示在画布上
    if game_status == 0:
        if this_game.status == 'attack':
            if now_time - this_game.action_start_time > 0.5:
                basic_position = 145
            else:
                basic_position = 145 + 430 * (0.5 - now_time + this_game.action_start_time)
            pygame.draw.rect(win, (60, 60, 60), (this_game.game_position, basic_position, 7 * Cube.WIDTH, 50))
            draw_text("ATTACK!", 35, (255, 0, 0), (this_game.game_position + 40, basic_position + 5))
            if now_time - this_game.action_start_time > 1:
                this_game.status = 'automove'
                this_game.active_cubes = (
                    Cube(this_game.game_position, 12, 3, this_game.next_color[0]), Cube(this_game.game_position, 13, 3, this_game.next_color[1]))
                this_game.pause_time += now_time - this_game.action_start_time
        elif this_game.status == 'defend':
            if now_time - this_game.action_start_time > 0.5:
                basic_position = 145
            else:
                basic_position = 145 - 290 * (0.5 - now_time + this_game.action_start_time)
            pygame.draw.rect(win, (60, 60, 60), (this_game.game_position, basic_position, 7 * Cube.WIDTH, 50))
            draw_text("DEFEND!", 35, (0, 255, 0), (this_game.game_position + 40, basic_position + 5))
            if now_time - this_game.action_start_time > 1:
                this_game.status = 'automove'
                this_game.active_cubes = (
                    Cube(this_game.game_position, 12, 3, this_game.next_color[0]), Cube(this_game.game_position, 13, 3, this_game.next_color[1]))
                this_game.pause_time += now_time - this_game.action_start_time

    # game_status为1，代表游戏结束，此时根据游戏胜利与否，提示win或lose，以及操作提示
    elif game_status == 1:
        if this_game.win:
            draw_text("YOU WIN!", 35, (255, 255, 255), (this_game.game_position + 26, 150), (100, 100, 100))
        else:
            draw_text("YOU LOSE!", 35, (255, 255, 255), (this_game.game_position + 12, 150), (100, 100, 100))
        draw_text("Press ENTER to restart", 18, (255, 255, 255), (this_game.game_position + 10, 200), (100, 100, 100))
        draw_text("Press ESC to quit", 18, (255, 255, 255), (this_game.game_position + 36, 220), (100, 100, 100))

    # game_status为2，代表手动暂停状态，提示可选操作
    elif game_status == 2:
        if this_game.status == 'active':
            draw_cube(this_game.active_cubes[0].x, this_game.active_cubes[0].y, Cube.WIDTH, Cube.HEIGHT, this_game.color_list[this_game.active_cubes[0].color])
            draw_cube(this_game.active_cubes[1].x, this_game.active_cubes[1].y, Cube.WIDTH, Cube.HEIGHT, this_game.color_list[this_game.active_cubes[1].color])
        draw_text("PAUSE", 40, (255, 255, 255), (this_game.game_position + 40, 150), (100, 100, 100))
        draw_text("Press SPACE to continue", 18, (255, 255, 255), (this_game.game_position + 4, 200), (100, 100, 100))
        draw_text("Press ENTER to restart", 18, (255, 255, 255), (this_game.game_position + 10, 220), (100, 100, 100))
        draw_text("Press ESC to quit", 18, (255, 255, 255), (this_game.game_position + 36, 240), (100, 100, 100))

    # 调用绘制游戏基本信息函数
    this_game.game_information_draw()

    return True

# AI基本操作行为函数，now_row、now_col代表活动方块所处的行数、列数
def ai_decide(this_game, now_row, now_col):
    active_cubes = this_game.active_cubes
    cubes = this_game.cubes
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
                cubes[col].append(Cube(this_game.game_position, len(cubes[col]), col, active_cubes[0].color))
                cubes[col].append(Cube(this_game.game_position, len(cubes[col]) + 1, col, active_cubes[1].color))
                this_game.cube_decide()
                score = - score_distribution[col] * 2
                for (c, r) in this_game.delete_list[0]:
                    score += score_distribution[c]
                score += 20 * len(this_game.delete_list[1])
                score_predict[(col, 0)] = score
                cubes[col].pop()
                cubes[col].pop()
                this_game.delete_list = [[], []]

                # 交换活动方块的颜色，再执行一次计算
                cubes[col].append(Cube(this_game.game_position, len(cubes[col]), col, active_cubes[1].color))
                cubes[col].append(Cube(this_game.game_position, len(cubes[col]) + 1, col, active_cubes[0].color))
                this_game.cube_decide()
                score = - score_distribution[col] * 2
                for (c, r) in this_game.delete_list[0]:
                    score += score_distribution[c]
                score += 20 * len(this_game.delete_list[1])
                score_predict[(col, 1)] = score
                cubes[col].pop()
                cubes[col].pop()
                this_game.delete_list = [[], []]

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
def order_generate(operation, col):
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

run = True  # 整个游戏是否运行
game_series = ()  # 游戏序列
now_time = time.time()  # 当前帧时间
game_pause_time = 0  # 整体游戏暂停时间
game_status = 3  # 0:游戏进行；1:游戏结束；2:手动暂停；3.模式选择；4.电脑难度选择
game_mode = 1  # 游戏模式，1代表一名玩家VS电脑，2代表两名玩家对抗
ai_type = 2  # AI类型，1:简单；2:普通；3:困难
special_brightness = 0.9  # 特殊方块的亮度
special_brightness_change = 0.01  # 每帧特殊方块亮度的变化

# 游戏运行循环
while run:
    # 计算20减去每帧运行的毫秒数，作为延时时间，保证在机能足够时每帧固定为20毫秒
    delay_time =  int(20 - 1000 * (time.time() - now_time))
    if delay_time < 0:
        delay_time = 0
    pygame.time.delay(delay_time)

    # 绘制画布的背景色为纯黑，计算当前帧时间、当前帧的操作信息
    win.fill((0, 0, 0))
    now_time = time.time()
    order = [[], []]

    # 若为游戏进行状态
    if game_status == 0:
        # 调整特殊方块亮度在0.9~1.25间"呼吸"变化
        special_brightness += special_brightness_change
        if special_brightness > 1.25:
            special_brightness_change = -0.01
        elif special_brightness < 0.9:
            special_brightness_change = 0.01

        # 获取按下的按键信息
        key_pressed = pygame.key.get_pressed()
        for index, this_game in enumerate(game_series):
            # 若为AI玩家且其分数大于等于100，则进行攻防判断
            if this_game.key_style == 0 and this_game.score >= 100:
                # 计算攻防系数，攻击系数为对方升起行数+底端中央行数+我方分数可攻击的行数，防御系数为我方升起行数+底端中央行数
                attack_index = 0
                for i, other_game in enumerate(game_series):
                    if i != index:
                        # 仅对方在'active'状态下才进行攻击，避免出现不可控意外被翻盘
                        if other_game.status == 'active':
                            attack_index = other_game.new_line + len(other_game.cubes[3]) + int(this_game.score // 100)
                        break
                defend_index = this_game.new_line + len(this_game.cubes[3])

                # 若防御系数达到10，则进行防御；但若正处在被攻击状态，则延迟0.5秒进行行动，方便人类玩家观察
                if defend_index >= 10:
                    if this_game.status == 'attack':
                        if now_time - this_game.action_start_time > 0.5:
                            order[index].append('d')
                    elif this_game.status == 'active':
                        order[index].append('d')

                # 若无需防御且攻击系数更高，则判断是否需要攻击
                elif attack_index >= defend_index:
                    # 简单电脑攻击倾向低，攻击判定的间隔长；普通电脑攻击倾向中等，攻击判定间隔中等；困难电脑倾向于积攒点数进行攻击，攻击判定间隔短
                    if this_game.ai_type == 1:
                        p = random.random()
                        if now_time - this_game.action_decide_time > 5:
                             if p < (attack_index - 5) / 20:
                                 order[index].append('a')
                                 this_game.action_decide_time = now_time + 5
                             else:
                                 this_game.action_decide_time = now_time
                    elif this_game.ai_type == 2:
                        p = random.random()
                        if now_time - this_game.action_decide_time > 3:
                             if p < (attack_index - 5) / 5:
                                 order[index].append('a')
                                 this_game.action_decide_time = now_time + 3
                             else:
                                 this_game.action_decide_time = now_time
                    elif this_game.ai_type == 3 and attack_index >= 10:
                        order[index].append('a')

            # 若游戏为'active'状态
            if this_game.status == 'active':
                # 若为人类玩家，判断是否按住向下键，决定下落速度
                if this_game.key_style > 0:
                    if key_pressed[this_game.key[1]]:
                        this_game.speed = 5
                    else:
                        this_game.speed = this_game.basic_speed

                # 若为AI玩家，若在掉落起始状态或下落位置已不可到达目标位置，则计算AI的移动
                else:
                    if this_game.active_cubes[0].y == -Cube.HEIGHT or (len(this_game.cubes[this_game.auto_target]) >= this_game.active_cubes[0].row and this_game.active_cubes[0].y % Cube.HEIGHT == 0):
                        now_row = int((360 - this_game.active_cubes[0].y) / Cube.HEIGHT) - 1
                        score_predict = ai_decide(this_game, now_row, this_game.active_cubes[0].col)  # 计算不同操作的价值
                        score_ordered = sorted(score_predict.items(), key=lambda x:x[1], reverse=True)  # 根据价值大小排序

                        # 简单电脑，在前三价值的选择中按一定概率分布选择
                        if this_game.ai_type == 1:
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
                        elif this_game.ai_type == 2:
                            p = random.random()
                            if p < 0.6 or len(score_ordered) <= 1:
                                operation_basic = score_ordered[0]
                            elif p < 0.9 or len(score_ordered) <= 2:
                                operation_basic = score_ordered[1]
                            else:
                                operation_basic = score_ordered[2]

                        # 困难电脑，必然选择最优价值选择
                        elif this_game.ai_type == 3:
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
                        this_game.auto_target = operation[0]
                        this_game.auto_order = order_generate(operation, this_game.active_cubes[0].col)

                    # 若操作指令列表已清空，则进行速降；否则按照一定的帧间隔调取其中一个操作
                    if len(this_game.auto_order) == 0:
                        this_game.speed = 5
                    else:
                        this_game.speed = this_game.basic_speed
                        this_game.ai_count += 1
                        if this_game.ai_count == this_game.ai_speed:
                            order[index].append(this_game.auto_order[0])
                            this_game.auto_order.pop(0)
                            this_game.ai_count = 0

    # 获取pygame事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        # 若存在按键事件
        elif event.type == pygame.KEYDOWN:
            # game_status为3，为游戏人数选择界面，按上、下键切换选择，回车键进行确定
            if game_status == 3:
                if event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                    thread_audio_play(move_audio)
                    if game_mode == 1:
                        game_mode = 2
                    else:
                        game_mode = 1
                elif event.key == pygame.K_RETURN:
                    thread_audio_play(confirm_audio)
                    # 选择的游戏人数为1，则进行AI难度选择页面，否则直接开始游戏
                    if game_mode == 1:
                        game_status = 4
                    else:
                        time.sleep(0.5)
                        game_series = (Game(20, 2, 2, 'PLAYER1'), Game(320, 2, 1, 'PLAYER2'))
                        game_status = 0
                        bgm_status = True

            # game_status为4，为AI难度选择界面，按上、下键切换选择，回车键进行确定
            elif game_status == 4:
                if event.key == pygame.K_UP:
                    thread_audio_play(move_audio)
                    ai_type -= 1
                    if ai_type < 1:
                        ai_type = 1
                elif event.key == pygame.K_DOWN:
                    thread_audio_play(move_audio)
                    ai_type += 1
                    if ai_type > 3:
                        ai_type = 3
                elif event.key == pygame.K_RETURN:
                    thread_audio_play(confirm_audio)
                    time.sleep(0.5)
                    game_series = (Game(20, 2, 0, 'COM', ai_type), Game(320, 2, 1, 'PLAYER'))
                    game_status = 0
                    bgm_status = True

            # game_status为2，为手动暂停状态，此时可以退出游戏、重新进行游戏或继续游戏
            elif game_status == 2:
                if event.key == pygame.K_ESCAPE:
                    run = False
                    continue
                elif event.key == pygame.K_RETURN:
                    thread_audio_play(confirm_audio)
                    game_status = 3
                elif event.key == pygame.K_SPACE:
                    pygame.mixer.music.unpause()
                    thread_audio_play(continue_audio)
                    game_pause_time += now_time - pause_start_time
                    for this_game in game_series:
                        this_game.pause_time += now_time - pause_start_time
                    game_status = 0

            # game_status为1，为游戏结束状态，此时可以退出游戏或重新进行游戏
            elif game_status == 1:
                if event.key == pygame.K_ESCAPE:
                    run = False
                    continue
                elif event.key == pygame.K_RETURN:
                    thread_audio_play(confirm_audio)
                    game_status = 3

            # game_status为0，为游戏进行状态，此时可以进行暂停、在'active'状态下操作活动方块或进行攻击、防御动作
            elif game_status == 0:
                if event.key == pygame.K_SPACE:
                    pygame.mixer.music.pause()
                    thread_audio_play(pause_audio)
                    pause_start_time = now_time
                    game_status = 2
                else:
                    for index, this_game in enumerate(game_series):
                        if this_game.key_style > 0:
                            if this_game.status == 'active':
                                if event.key == this_game.key[2]:
                                    order[index].append('l')
                                elif event.key == this_game.key[3]:
                                    order[index].append('r')
                                if event.key == this_game.key[0]:
                                    order[index].append('s')
                            if event.key == this_game.key[5]:
                                order[index].append('d')
                            elif event.key == this_game.key[4]:
                                order[index].append('a')

    if game_status < 3:
        # 根据操作指令，控制活动方块左右移动、交换颜色以及进行攻击或防御动作
        for index, this_game in enumerate(game_series):
            if 'l' in order[index]:
                move_status = this_game.active_cubes[0].col_change(-1)
                if move_status:
                    if len(this_game.cubes[this_game.active_cubes[0].col]) >= this_game.active_cubes[0].row:
                        this_game.active_cubes[0].col_change(1)
                        move_status = False
                if move_status:
                    this_game.active_cubes[1].col_change(-1)
                    thread_audio_play(move_audio)
            elif 'r' in order[index]:
                move_status = this_game.active_cubes[0].col_change(1)
                if move_status:
                    if len(this_game.cubes[this_game.active_cubes[0].col]) >= this_game.active_cubes[0].row:
                        this_game.active_cubes[0].col_change(-1)
                        move_status = False
                if move_status:
                    this_game.active_cubes[1].col_change(1)
                    thread_audio_play(move_audio)
            if 's' in order[index]:
                this_game.active_cubes[0].color, this_game.active_cubes[1].color = \
                    this_game.active_cubes[1].color, this_game.active_cubes[0].color
                thread_audio_play(change_audio)
            if 'd' in order[index]:
                if this_game.score >= 100:
                    delete_line = int(this_game.score // 100)
                    this_game.delete_line += delete_line
                    if this_game.status == 'attack':
                        this_game.pause_time += now_time - this_game.action_start_time
                    this_game.action_start_time = now_time
                    this_game.status = 'defend'
                    this_game.score = 0
                    thread_audio_play(defend_audio)
            elif 'a' in order[index]:
                if this_game.score >= 100:
                    for i, other_game in enumerate(game_series):
                        if i != index:
                            other_game.new_line += int(this_game.score // 100)
                            if other_game.status == 'defend':
                                other_game.pause_time += now_time - other_game.action_start_time
                            other_game.action_start_time = now_time
                            other_game.status = 'attack'
                    this_game.score = 0
                    thread_audio_play(attack_audio)

            # 调用游戏进行函数，若返回False，说明此游戏已失败，则对手获胜，游戏结束
            result = game_run(this_game)
            if not result:
                this_game.win = False
                game_status = 1
                bgm_status = False
                if game_mode == 1 and this_game.key_style > 0:
                    thread_audio_play(fail_audio)
                else:
                    thread_audio_play(victory_audio)

    # 若在游戏人数选择界面，绘制基本信息
    elif game_status == 3:
        draw_text("Please choose a mode", 20, (255, 255, 255), (200, 200))
        if game_mode == 1:
            draw_text("1 PLAYER", 20, (255, 255, 0), (250, 130))
            draw_text("2 PLAYER", 20, (255, 255, 255), (250, 150))
        else:
            draw_text("1 PLAYER", 20, (255, 255, 255), (250, 130))
            draw_text("2 PLAYER", 20, (255, 255, 0), (250, 150))

    # 若在AI难度选择界面，绘制基本信息
    elif game_status == 4:
        draw_text("Please choose difficulty", 20, (255, 255, 255), (200, 200))
        if ai_type == 1:
            draw_text("EASY", 20, (255, 255, 0), (250, 130))
            draw_text("NORMAL", 20, (255, 255, 255), (250, 150))
            draw_text("HARD", 20, (255, 255, 255), (250, 170))
        elif ai_type == 2:
            draw_text("EASY", 20, (255, 255, 255), (250, 130))
            draw_text("NORMAL", 20, (255, 255, 0), (250, 150))
            draw_text("HARD", 20, (255, 255, 255), (250, 170))
        elif ai_type == 3:
            draw_text("EASY", 20, (255, 255, 255), (250, 130))
            draw_text("NORMAL", 20, (255, 255, 255), (250, 150))
            draw_text("HARD", 20, (255, 255, 0), (250, 170))

    pygame.display.update()  # 更新画布

pygame.quit()  # 若退出循环，游戏退出