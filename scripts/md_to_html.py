# -*- coding: utf-8 -*-
"""
Markdown到微信公众号HTML转换器
支持自动识别金句、高亮块、引用等特殊语法
"""

import re
from typing import List, Tuple


class MarkdownToHTML:
    """Markdown转HTML转换器"""

    def __init__(self):
        """初始化转换器"""
        self.styles = self._load_styles()

    def _load_styles(self) -> dict:
        """加载样式定义"""
        return {
            'golden_quote': {
                'container': 'background: #f0fbf4; border-left: 4px solid #38c76e; font-size: 18px; font-weight: bold; color: #2d3436; padding: 20px; border-radius: 8px; margin: 25px 0; line-height: 1.8;',
            },
            'main_title': {
                'container': 'font-size: 22px; font-weight: bold; color: #244b3a; margin-top: 42px; margin-bottom: 22px; line-height: 1.45;',
            },
            'highlight_box': {
                'container': 'background: #eaf7f0; border-radius: 8px; padding: 20px; margin: 25px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.08);',
                'title': 'font-size: 16px; font-weight: bold; color: #38c76e; margin-bottom: 12px;',
                'content': 'font-size: 15px; line-height: 1.8; color: #333;',
            },
            'blockquote': {
                'container': 'border-left: 3px solid #38c76e; background: #f5f5f5; font-style: italic; padding: 15px 20px; margin: 25px 0; color: #555; line-height: 1.8; border-radius: 4px;',
                'source': 'font-size: 13px; color: #888; margin-top: 10px; font-style: normal;',
            },
            'section_title': {
                'container': 'font-size: 19px; font-weight: bold; color: #2f7d52; margin-top: 40px; margin-bottom: 20px; padding-left: 15px; border-left: 5px solid #38c76e; line-height: 1.4;',
            },
            'paragraph': {
                'container': 'font-size: 16px; line-height: 1.9; color: #333; margin-bottom: 25px;',
            },
            'hr': {
                'container': 'border: none; border-top: 2px solid #e3efe8; margin: 40px 0;',
            }
        }

    def convert(self, markdown_text: str, mode: str = 'personal') -> str:
        """
        将Markdown文本转换为微信公众号HTML

        Args:
            markdown_text: Markdown格式的文本
            mode: 写作模式 ('company' 或 'personal')

        Returns:
            HTML格式的文本
        """
        lines = markdown_text.split('\n')
        html_lines = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行
            if not line:
                i += 1
                continue

            # 处理小节标题 (### 开头)
            if line.startswith('# '):
                title = line[2:].strip()
                html_lines.append(self._create_main_title(title))
                i += 1
                continue

            if line.startswith('### '):
                title = line[4:].strip()
                html_lines.append(self._create_section_title(title))
                i += 1
                continue

            # 处理高亮块 ([[高亮:标题|内容]])
            if line.startswith('[[高亮:') and ']]' in line:
                content = self._parse_highlight_block(line)
                html_lines.append(content)
                i += 1
                continue

            # 处理引用块 (> 开头)
            if line.startswith('> '):
                blockquote_lines = []
                while i < len(lines) and lines[i].strip().startswith('> '):
                    blockquote_lines.append(lines[i].strip()[2:])
                    i += 1
                html_lines.append(self._create_blockquote(blockquote_lines))
                continue

            # 处理金句 ("""包裹 或 **加粗**)
            if line.startswith('"""') or line.startswith('**') and line.endswith('**'):
                content = self._parse_golden_quote(line)
                if content:
                    html_lines.append(content)
                    i += 1
                    continue

            # 处理普通段落
            paragraph_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#', '>', '[[')):
                paragraph_lines.append(lines[i].strip())
                i += 1
                if i < len(lines) and not lines[i].strip():
                    break

            if paragraph_lines:
                paragraph_text = ' '.join(paragraph_lines)
                html_lines.append(self._create_paragraph(paragraph_text))

        return '\n'.join(html_lines)

    def _create_main_title(self, title: str) -> str:
        return f'<h1 style="{self.styles["main_title"]["container"]}">{title}</h1>'

    def _create_section_title(self, title: str) -> str:
        """创建小节标题"""
        return f'<h3 style="{self.styles["section_title"]["container"]}">{title}</h3>'

    def _create_paragraph(self, text: str) -> str:
        """创建普通段落,支持行内加粗"""
        # 处理行内加粗 **文字**
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong style="font-weight: bold; color: #38c76e;">\1</strong>', text)

        # 处理链接 [文字](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #38c76e; text-decoration: none; border-bottom: 1px solid transparent;">\1</a>', text)

        return f'<p style="{self.styles["paragraph"]["container"]}">{text}</p>'

    def _parse_golden_quote(self, line: str) -> str:
        """解析金句"""
        # 方式一: 三引号包裹
        if line.startswith('"""') and line.endswith('"""'):
            text = line[3:-3].strip()
            return f'<div style="{self.styles["golden_quote"]["container"]}">"{text}"</div>'

        # 方式二: 完整行加粗
        if line.startswith('**') and line.endswith('**'):
            text = line[2:-2].strip()
            return f'<div style="{self.styles["golden_quote"]["container"]}">"{text}"</div>'

        return None

    def _parse_highlight_block(self, line: str) -> str:
        """解析高亮块 [[高亮:标题|内容]]"""
        # 移除 [[高亮: 和 ]]
        content = line[6:-2].strip()

        if '|' in content:
            title, content_text = content.split('|', 1)
            title = title.strip()
            content_text = content_text.strip()
        else:
            title = '要点'
            content_text = content

        title_html = f'<div style="{self.styles["highlight_box"]["title"]}">📌 {title}</div>'
        content_html = f'<div style="{self.styles["highlight_box"]["content"]}">{content_text}</div>'

        return f'<div style="{self.styles["highlight_box"]["container"]}">{title_html}{content_html}</div>'

    def _create_blockquote(self, lines: List[str]) -> str:
        """创建引用块"""
        # 分离引用内容和出处
        content_lines = []
        source = None

        for i, line in enumerate(lines):
            # 检查是否是出处 (通常在最后一行,包含 "—" 或 "出自" 等)
            if i == len(lines) - 1 and ('—' in line or '出自' in line or '来源' in line):
                source = line.replace('—', '').replace('出自', '').replace('来源', '').strip()
            else:
                content_lines.append(line)

        content_text = ' '.join(content_lines)
        content_html = f'<div style="{self.styles["blockquote"]["container"]}">{content_text}'

        if source:
            content_html += f'<div style="{self.styles["blockquote"]["source"]}">— {source}</div>'

        content_html += '</div>'

        return content_html

    def add_company_ending(self, html_content: str, qrcode_url: str = None) -> str:
        """
        为公司模式添加固定结尾

        Args:
            html_content: 原始HTML内容
            qrcode_url: 二维码图片URL

        Returns:
            添加了固定结尾的HTML内容
        """
        ending_html = f'''
<div style="margin-top: 50px; padding-top: 30px; border-top: 2px solid #e0e0e0;">
  <p style="font-size: 15px; line-height: 1.9; color: #333; margin-bottom: 20px;">
    迪康合成中心，深耕生物材料创新领域，始终以客户需求为核心锚点，构建全周期定制化服务生态。从项目前期的专业咨询、精准化材料研发设计，到规模化生产的高效落地，再到售后阶段的全方位保障，我们坚守"客户至上"的核心理念，持续迭代服务流程与运营体系，以精益求精的态度打造极致客户体验。同时，我们建立了高标准的供应链管控机制，确保材料供应的安全性、稳定性与可靠性，全方位响应并满足客户多元化、个性化需求。
  </p>
'''

        if qrcode_url:
            ending_html += f'''
  <p style="text-align: center; margin: 30px 0;">
    <img src="{qrcode_url}" style="max-width: 200px; height: auto;" alt="扫码查看移动店铺">
  </p>
  <p style="font-size: 14px; color: #666; text-align: center; margin-bottom: 10px;">
    扫码查看移动店铺
  </p>
'''

        ending_html += '''
  <p style="font-size: 15px; line-height: 1.8; color: #1a5490; font-weight: bold; margin-top: 30px;">
    #聚焦生物医用材料前沿，洞察医疗器械产业未来。如果你对丙交酯或聚乳酸产业还有其他疑问，或者想了解更多相关资讯，欢迎在评论区留言。
  </p>
</div>
'''

        return html_content + ending_html

    def wrap_in_container(self, html_content: str) -> str:
        """将内容包装在容器中"""
        font_stack = "\"PingFang SC\", -apple-system, BlinkMacSystemFont, \"Helvetica Neue\", Arial, sans-serif"
        return f'<section style="font-family: {font_stack};">{html_content}</section>'


# 便捷函数
def markdown_to_html(markdown_text: str, mode: str = 'personal', qrcode_url: str = None) -> str:
    """
    将Markdown转换为微信公众号HTML

    Args:
        markdown_text: Markdown文本
        mode: 模式 ('company' 或 'personal')
        qrcode_url: 二维码URL(仅公司模式需要)

    Returns:
        HTML文本
    """
    converter = MarkdownToHTML()

    # 转换Markdown到HTML
    html_content = converter.convert(markdown_text, mode)

    # 如果是公司模式,添加固定结尾
    if mode == 'company':
        html_content = converter.add_company_ending(html_content, qrcode_url)

    # 包装在容器中
    html_content = converter.wrap_in_container(html_content)

    return html_content


if __name__ == '__main__':
    # 测试代码
    test_markdown = """你有没有发现,最近医美圈聊童颜针的朋友越来越多了?

**真正的年轻化不是简单地填平皱纹，而是恢复组织的活力和再生能力。**

### PLLA的技术演进

> PLLA代表了一类重要的生物刺激剂，它通过激活宿主反应来产生治疗效果。
> — Dermatologic Surgery 2024

[[高亮:核心优势|PLLA效果可持续长达2年,是很多其他填充剂难以比拟的。]]
"""

    html = markdown_to_html(test_markdown, mode='personal')

    # 输出到文件避免控制台编码问题
    import sys
    from pathlib import Path
    output_file = Path(__file__).parent.parent / 'test_output.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"测试成功!HTML已输出到: {output_file}")
