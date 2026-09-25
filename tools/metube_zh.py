# -*- coding: utf-8 -*-
"""
把 MeTube 原版前端（Angular 编译产物 main-*.js）汉化。

原理：不重新构建 Angular 项目，只对编译产物做「限定语法位置」的字符串替换。
     UI 文本在编译产物中只出现在固定位置，逐类替换即可，绝不误伤代码标识符。

用法：
    python metube_zh.py <dist目录>            # 就地把 dist/main-*.js 汉化
    python metube_zh.py <dist目录> --out <目录>

拿到 dist 的办法（MeTube 未设认证时可直接下载）：
    curl -O http://<host>:7878/            # index.html，里面能看到 main-<hash>.js 等文件名
    curl -O http://<host>:7878/main-<hash>.js
    curl -O http://<host>:7878/styles-<hash>.css
    curl -O http://<host>:7878/polyfills-<hash>.js
    # 以及 favicon.ico / manifest.webmanifest / assets/icons/*
    # index.html 记得把 <html lang="en"> 改成 zh-CN、<noscript> 文案翻译

替换后必须校验：
    node --input-type=module --check < main-*.js     # 语法必须通过
"""
import argparse
import glob
import os
import re
import shutil

# ============ 一、替换规则 ============
# mode 的含义：
#   text  仅 b(N,"X")             —— Angular ɵɵtext 文本节点（最安全，优先用它）
#   attr  仅 "placeholder|title|aria-label|alt","X"
#   opt   仅 text:"X"             —— 下拉选项显示名（{id:"best",text:"Best"}）
#   disp  仅 displayName:"X"      —— 主题等显示名
#   cfg   仅 xxxText="X"          —— ng-select 内置文案
#   ve    仅 Ve(...) 调用内部      —— 插值文本
#   lang  subtitleLanguages 段内
#   raw   全局精确替换（**只用于已逐条核查、所有出现均为界面文本的词**）
#
# ⚠️ 踩过的坑：Format / URL / Active / Default / None / Delete / Any 在 Angular 内部
#    枚举、KeyboardEvent 键名、XHR 构造、Sanitizer 里同名出现，绝不能 raw 替换，
#    必须用 text / attr 等受限 mode。
T = [
    # ===== 主按钮 / 状态（带前后空格的原样保留空格，否则拼接会粘连） =====
    (" Download ", " 下载 ", "raw"),
    (" Subscribe ", " 订阅 ", "raw"),
    (" Adding... ", " 添加中… ", "raw"),
    (" Subscribing... ", " 订阅中… ", "raw"),
    (" Canceling... ", " 取消中… ", "raw"),
    (" Connecting to server... ", " 正在连接服务器… ", "raw"),
    (" Cookies active ", " Cookies 已生效 ", "raw"),
    (" No cookies configured ", " 未配置 Cookies ", "raw"),
    (" Waiting for stream ", " 等待直播开始 ", "raw"),
    (" Advanced Options ", " 高级选项 ", "raw"),
    (" Import URLs ", " 导入链接 ", "raw"),
    (" Copy URLs ", " 复制链接 ", "raw"),
    (" Export URLs ", " 导出链接 ", "raw"),
    (" Cancel Import ", " 取消导入 ", "raw"),
    ("Batch Import URLs", "批量导入链接", "raw"),
    ("Cancel", "取消", "raw"),
    (" Cancel ", " 取消 ", "raw"),
    ("Close", "关闭", "raw"),
    ("Save", "保存", "raw"),
    ("Edit", "编辑", "raw"),

    # ===== 区块 / 表单标签 =====
    ("Tools", "工具", "raw"),
    ("Behavior", "行为", "raw"),
    ("Bulk Actions", "批量操作", "raw"),
    ("Output", "输出", "raw"),
    ("Option Presets", "选项预设", "raw"),
    ("Custom yt-dlp Options", "自定义 yt-dlp 参数", "raw"),
    ("Subscriptions", "订阅管理", "raw"),
    ("Template", "模板", "raw"),
    ("Type", "类型", "raw"),
    ("Quality", "清晰度", "raw"),
    ("Codec", "编码", "raw"),
    ("Codec / Format", "编码 / 格式", "raw"),
    ("Name", "名称", "raw"),
    ("Status", "状态", "raw"),
    ("Speed", "速度", "raw"),
    ("ETA", "剩余时间", "raw"),
    ("File Size", "文件大小", "raw"),
    ("Language", "字幕语言", "raw"),
    ("Subtitle Source", "字幕来源", "raw"),
    ("Auto Start", "自动开始", "raw"),
    ("Custom Name Prefix", "自定义文件名前缀", "raw"),
    ("Download Folder", "下载目录", "raw"),
    ("Split by chapters", "按章节分割", "raw"),
    ("Remove sponsor segments", "移除赞助片段", "raw"),
    ("Clip start", "片段开始", "raw"),
    ("Clip end", "片段结束", "raw"),
    ("Items Limit", "条数上限", "raw"),
    ("Interval (min)", "检查间隔（分钟）", "raw"),
    ("Subscription Check (min)", "订阅检查（分钟）", "raw"),
    ("Subscription Title Filter", "订阅标题过滤", "raw"),
    ("Last checked", "上次检查", "raw"),
    ("Skip members-only subscription videos", "跳过会员专属视频", "raw"),
    ("Downloading", "正在下载", "raw"),
    ("Completed", "已完成", "raw"),
    ("Queued", "排队中", "raw"),
    ("Downloaded", "已下载", "raw"),
    ("Post-processing", "后期处理", "raw"),
    ("LIVE", "直播", "raw"),
    ("Yes", "是", "raw"),
    ("No", "否", "raw"),
    ("Copied!", "已复制！", "raw"),
    ("Error:", "错误：", "raw"),
    ("Message:", "消息：", "raw"),
    ("Unknown Error", "未知错误", "raw"),
    ("Select all", "全选", "raw"),
    ("Select item", "选择条目", "raw"),
    ("Click for details ", "点击查看详细信息 ", "raw"),
    ("Filter", "筛选", "raw"),

    # ===== 与代码标识符同名，必须限定位置 =====
    ("Format", "格式", "text"),
    ("URL", "链接", "text"),
    ("URL:", "链接：", "text"),
    ("Active", "已启用", "text"),
    ("Paused", "已暂停", "text"),
    ("Default", "默认", "attr"),

    # ===== 下拉选项显示名 =====
    ("Video", "视频", "raw"),
    ("Audio", "音频", "opt"),
    ("Captions", "字幕", "opt"),
    ("Thumbnail", "封面", "opt"),
    ("Best", "最佳", "opt"),
    ("Worst", "最差", "opt"),
    ("Auto", "自动", "opt"),
    ("iOS Compatible", "iOS 兼容", "opt"),
    ("TXT (Text only)", "TXT（纯文本）", "opt"),
    ("Prefer Auto", "优先自动", "opt"),
    ("Prefer Manual", "优先手动", "opt"),
    ("Auto Only", "仅自动", "opt"),
    ("Manual Only", "仅手动", "opt"),
    ("Light", "浅色", "disp"),
    ("Dark", "深色", "disp"),
    ("Auto", "自动", "disp"),

    # ===== ng-select 内置文案 =====
    ("No items found", "未找到条目", "cfg"),
    ("Type to search", "输入以搜索", "cfg"),
    ("Add item", "添加条目", "cfg"),
    ("Loading...", "加载中…", "cfg"),
    ("Clear all", "清除全部", "cfg"),
    ("Remove", "移除", "cfg"),
    ("Options List", "选项列表", "raw"),

    # ===== 订阅启停 / 排序 / 单位 =====
    ("Pause", "暂停", "raw"),
    ("Resume", "继续", "raw"),
    ("Pause ", "暂停 ", "raw"),
    ("Resume ", "继续 ", "raw"),
    ("Newest first", "最新在前", "raw"),
    ("Oldest first", "最早在前", "raw"),
    ("0 Bytes", "0 字节", "raw"),
    ("Bytes", "字节", "raw"),

    # ===== 提示 / 错误消息 =====
    ("Delete failed", "删除失败", "raw"),
    ("Start download failed", "开始下载失败", "raw"),
    ("Subscribe failed", "订阅失败", "raw"),
    ("Delete subscription failed", "删除订阅失败", "raw"),
    ("Delete subscriptions failed", "删除订阅失败", "raw"),
    ("Update subscription failed", "更新订阅失败", "raw"),
    ("Refresh subscriptions failed", "刷新订阅失败", "raw"),
    ("Subscription check failed", "订阅检查失败", "raw"),
    ("Clear completed failed", "清除已完成失败", "raw"),
    ("Clear failed downloads failed", "清除失败下载失败", "raw"),
    ("Please enter a URL", "请输入链接", "raw"),
    ("Request failed", "请求失败", "raw"),
    ("Try anyway", "仍然尝试", "raw"),

    # ===== 批量操作按钮（\xA0 为原版前导不换行空格，必须保留转义写法） =====
    ("\\xA0 Download Selected", "\\xA0 下载所选", "raw"),
    ("\\xA0 Download selected", "\\xA0 下载所选", "raw"),
    ("\\xA0 Clear completed", "\\xA0 清除已完成", "raw"),
    ("\\xA0 Clear failed", "\\xA0 清除失败", "raw"),
    ("\\xA0 Retry failed", "\\xA0 重试失败项", "raw"),
    ("\\xA0 Clear selected", "\\xA0 清除所选", "raw"),
    ("\\xA0 Delete selected ", "\\xA0 删除所选 ", "raw"),
    ("\\xA0 Cancel selected", "\\xA0 取消所选", "raw"),
    ("\\xA0 Check selected ", "\\xA0 检查所选 ", "raw"),
    ("\\xA0 Check all now ", "\\xA0 立即检查全部 ", "raw"),
    ("Check now ", "立即检查 ", "raw"),
    ("Check all now ", "立即检查全部 ", "raw"),
    ("Check selected ", "检查所选 ", "raw"),
    ("Checking ", "检查中 ", "raw"),

    # ===== 无障碍标签 / title / placeholder =====
    ("Cancel adding URL", "取消添加链接", "attr"),
    ("Download or subscribe", "下载或订阅", "attr"),
    ("Open source URL for ", "打开源链接：", "attr"),
    ("Download result file for ", "下载结果文件：", "attr"),
    ("Download chapter file ", "下载章节文件：", "attr"),
    ("Open chapter file ", "打开章节文件：", "attr"),
    ("Share result file for ", "分享结果文件：", "attr"),
    ("Retry download for ", "重试下载：", "attr"),
    ("Start download for ", "开始下载：", "attr"),
    ("Delete completed item ", "删除已完成项：", "attr"),
    ("Delete subscription ", "删除订阅：", "attr"),
    ("Select subscription ", "选择订阅：", "attr"),
    ("Select all subscriptions", "全选订阅", "attr"),
    ("Toggle error details for ", "展开/收起错误详情：", "attr"),
    ("Subscription name for ", "订阅名称：", "attr"),
    ("Select item ", "选择条目：", "attr"),
    ("Select all ", "全选", "attr"),
    ("Remove ", "移除：", "attr"),
    ("Enter video, channel, or playlist URL", "输入视频、频道或播放列表链接", "attr"),
    ("Paste one video URL per line", "每行粘贴一个视频链接", "attr"),
    ("Optional regex", "可选正则表达式", "attr"),
    ("e.g. 2:26", "例如 2:26", "attr"),
    ("e.g. 3:24", "例如 3:24", "attr"),
    ("MeTube Logo", "MeTube 标识", "attr"),

    # ===== 插值文本（Ve 调用内） =====
    (" downloading", " 个正在下载", "ve"),
    (" queued", " 个排队中", "ve"),
    (" completed", " 个已完成", "ve"),
    (" failed", " 个失败", "ve"),
    (" - starts in ", " - 将于 ", "raw"),
    ("Upload Cookies", "上传 Cookies", "ve"),
    ("Replace Cookies", "替换 Cookies", "ve"),
]

# 字幕语言下拉（subtitleLanguages 数组内的 text:"X"）
LANGS = {
    "English": "英语", "Arabic": "阿拉伯语", "Bengali": "孟加拉语", "Bulgarian": "保加利亚语",
    "Catalan": "加泰罗尼亚语", "Czech": "捷克语", "Danish": "丹麦语", "Dutch": "荷兰语",
    "Spanish": "西班牙语", "Estonian": "爱沙尼亚语", "Finnish": "芬兰语", "French": "法语",
    "German": "德语", "Greek": "希腊语", "Hebrew": "希伯来语", "Hindi": "印地语",
    "Hungarian": "匈牙利语", "Indonesian": "印尼语", "Italian": "意大利语",
    "Lithuanian": "立陶宛语", "Latvian": "拉脱维亚语", "Malay": "马来语", "Norwegian": "挪威语",
    "Polish": "波兰语", "Portuguese": "葡萄牙语", "Portuguese (Brazil)": "葡萄牙语（巴西）",
    "Romanian": "罗马尼亚语", "Russian": "俄语", "Slovak": "斯洛伐克语",
    "Slovenian": "斯洛文尼亚语", "Serbian": "塞尔维亚语", "Swedish": "瑞典语",
    "Tamil": "泰米尔语", "Telugu": "泰卢固语", "Thai": "泰语", "Turkish": "土耳其语",
    "Ukrainian": "乌克兰语", "Urdu": "乌尔都语", "Vietnamese": "越南语", "Japanese": "日语",
    "Korean": "韩语", "Chinese (Simplified)": "中文（简体）",
    "Chinese (Traditional)": "中文（繁体）",
}

# ============ 二、运行时拼接函数补丁 ============
# 表格单元格里的「类型/清晰度/编码」不是模板文本，而是 JS 用 charAt(0).toUpperCase()
# 现场拼出来的（"video"→"Video"），必须直接改函数实现，否则永远是英文。
PATCHES = [
    ('let e=n.download_type||"video";return e.charAt(0).toUpperCase()+e.slice(1)',
     'let e=n.download_type||"video";return{video:"视频",audio:"音频",captions:"字幕",thumbnail:"封面"}[e]??e.charAt(0).toUpperCase()+e.slice(1)'),
    (r'/^\d+$/.test(e)?`${e}p`:e.charAt(0).toUpperCase()+e.slice(1)',
     r'/^\d+$/.test(e)?`${e}p`:({best:"最佳",worst:"最差"}[e]??e.charAt(0).toUpperCase()+e.slice(1))'),
    ('return!e||e==="auto"?"Auto":this.videoCodecs.find(i=>i.id===e)?.text??e',
     'return!e||e==="auto"?"自动":this.videoCodecs.find(i=>i.id===e)?.text??e'),
]


def esc(s):
    return re.escape(s)


def apply_mode(text, en, cn, mode):
    n = 0
    if mode == "text":
        pat = re.compile(r'(\bb\(\s*\d+\s*,\s*)"' + esc(en) + r'"')
        text, n = pat.subn(lambda m: m.group(1) + '"' + cn + '"', text)
    elif mode == "attr":
        pat = re.compile(r'("(?:placeholder|title|aria-label|alt)","?)' + esc(en) + r'(")')
        text, n = pat.subn(lambda m: m.group(1) + cn + m.group(2), text)
    elif mode == "opt":
        pat = re.compile(r'(\btext:")' + esc(en) + r'(")')
        text, n = pat.subn(lambda m: m.group(1) + cn + m.group(2), text)
    elif mode == "disp":
        pat = re.compile(r'(\bdisplayName:")' + esc(en) + r'(")')
        text, n = pat.subn(lambda m: m.group(1) + cn + m.group(2), text)
    elif mode == "cfg":
        pat = re.compile(r'(\b\w*Text=")' + esc(en) + r'(")')
        text, n = pat.subn(lambda m: m.group(1) + cn + m.group(2), text)
    elif mode == "ve":
        def repl(m):
            nonlocal n
            new, k = re.subn(r'(")' + esc(en) + r'(")', lambda x: x.group(1) + cn + x.group(2), m.group(0))
            n += k
            return new
        text = re.sub(r'\bVe\([^()]*\)', repl, text)
    elif mode == "raw":
        pat = re.compile(r'(")' + esc(en) + r'(")')
        text, n = pat.subn(lambda m: m.group(1) + cn + m.group(2), text)
    return text, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", help="包含 main-*.js 的目录")
    ap.add_argument("--out", default=None, help="输出目录（默认就地替换，会先备份 .orig）")
    a = ap.parse_args()

    files = glob.glob(os.path.join(a.dist, "main-*.js"))
    if not files:
        raise SystemExit("未找到 main-*.js")
    src_path = files[0]
    src = open(src_path, encoding="utf-8").read()
    orig_len = len(src)
    print("bundle:", src_path, orig_len, "chars")

    if a.out:
        os.makedirs(a.out, exist_ok=True)
        for f in os.listdir(a.dist):
            p = os.path.join(a.dist, f)
            d = os.path.join(a.out, f)
            shutil.copytree(p, d) if os.path.isdir(p) else shutil.copy2(p, d)
        out_path = os.path.join(a.out, os.path.basename(src_path))
    else:
        if not os.path.exists(src_path + ".orig"):
            shutil.copy2(src_path, src_path + ".orig")
        out_path = src_path

    missed = []
    for en, cn, mode in T:
        src, n = apply_mode(src, en, cn, mode)
        if n == 0:
            missed.append((en, mode))

    # 字幕语言列表
    i = src.find("subtitleLanguages=[")
    if i >= 0:
        j = src.find("];", i)
        seg = src[i:j]
        for en, cn in LANGS.items():
            seg = re.sub(r'(\btext:")' + re.escape(en) + r'(")', lambda m: m.group(1) + cn + m.group(2), seg)
        src = src[:i] + seg + src[j:]

    # 运行时拼接函数
    for old, new in PATCHES:
        cnt = src.count(old)
        if cnt != 1:
            print("⚠️ PATCH 匹配数异常(%d)（MeTube 版本可能变了，请人工核对）：%s" % (cnt, old[:60]))
            missed.append((old[:40], "patch"))
            continue
        src = src.replace(old, new)

    open(out_path, "w", encoding="utf-8").write(src)
    print("size: %d -> %d" % (orig_len, len(src)))
    if missed:
        print("未命中 %d 条（版本差异，需人工确认）：" % len(missed))
        for m in missed:
            print("   ", m)
    else:
        print("全部规则命中 ✅")
    print("\n下一步：node --input-type=module --check < %s" % out_path)


if __name__ == "__main__":
    main()
