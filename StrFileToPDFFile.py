#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(r"./reportlabSrc.zip")
import argparse
import reportlab.lib.pagesizes
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import units
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

marginTop = 2.0
marginBottom = 2.0
marginLeft = 2.0
marginRight = 2.0


class Margins(object):
    def __init__(self, right, left, top, bottom):
        self._right = right
        self._left = left
        self._top = top
        self._bottom = bottom

    @property
    def right(self):
        return self._right * units.cm

    @property
    def left(self):
        return self._left * units.cm

    @property
    def top(self):
        return self._top * units.cm

    @property
    def bottom(self):
        return self._bottom * units.cm

    def adjustLeft(self, width):
        self._left -= width / units.cm


class PDFCreator(object):
    
    # 字体大小
    fontSize = 10
    # 额外行距
    extraVerticalSpace = 0.0
    # 字符间距
    kerning = 0.0
    # 纸张大小
    media ="A4"
    # 是否横向打印
    landscape = False
    # 是否冗余输出
    verbose = True
    # 输入文件的编码
    encoding = "utf-8"
    # 是否输出页码
    pageNumbers = False
    # 输入文件名
    fileName = ""
    # 后缀名
    newFileSuffixName = r".pdf"
    # 字体路径
    fontPath = r"./simsun.ttc"
    # 是否添加页码
    pageNumbering = False
               
	# 判断文件或文件夹是否存在
    def _isExist(self, dir):
		return True if os.path.exists(dir) else False

    def __init__(self, args, margins):
        if len(args) == 0:
            raise Exception(u"请输入源文件名", 0)
            
        self.fileName = args[0]
        if not self._isExist(self.fileName):
            raise Exception(u"源文件不存在", 0)
            
        (dirname, basename) = os.path.split(self.fileName)
        pointIndex = basename.rfind(r".")
        newBasename = basename + self.newFileSuffixName \
            if pointIndex < 0 else basename[:pointIndex] + self.newFileSuffixName
            
        self.output = (dirname + "\\" if dirname != "" else "") + newBasename
            
        # 将pagesizes中的常量返回
        pageWidth, pageHeight = reportlab.lib.pagesizes.__dict__[self.media]
        # 是否横向打印
        if self.landscape:
            pageWidth, pageHeight = reportlab.lib.pagesizes.landscape(
                (pageWidth, pageHeight))
        # 设置pdf信息开始---------
        self.canvas = Canvas(self.output, pagesize=(pageWidth, pageHeight))
        # 设置pdf信息结束---------
        # 设置字体（大小，类型）开始--------
        self.font = 'myFont'
        pdfmetrics.registerFont(TTFont('myFont', self.fontPath))
        # 设置字体（大小，类型）结束--------
        # 外边距
        self.margins = margins
        # 行距
        self.leading = (self.extraVerticalSpace+ 1.2) * self.fontSize
        # 每页行数
        self.linesPerPage = int(
            (self.leading + pageHeight
             - margins.top - margins.bottom - self.fontSize) / self.leading)
        # 获取字体宽度（"."的宽度，与中文宽度不同）
        self.fontWidth = self.canvas.stringWidth(
            ".", fontName=self.font, fontSize=self.fontSize)
        # 内容宽度
        contentWidth = pageWidth - margins.left - margins.right
        # 每行字符数
        self.charsPerLine = int(
            (contentWidth + self.kerning) / (self.fontWidth + self.kerning))
        # ?内容顶部坐标
        self.top = pageHeight - margins.top - self.fontSize
        # 是否添加页码
        if self.pageNumbering:
            # 页码位置
            self.pageNumberPlacement = \
               (pageWidth / 2, margins.bottom / 2)

    def _process(self, data):
        # 文件大小
        flen = os.fstat(data.fileno()).st_size
        # 记录被读取文件的当前行索引
        lineno = 0
        read = 0
        # 一行一行读取
        for line in data:
            lineno += 1
            # 获取python版本
            if sys.version_info.major == 2:
                # 记录当前累计读取的总字节数
                read += len(line)
                yield flen == \
                    read, lineno, line.decode(self.encoding).rstrip('\r\n')
            else:
                read += len(line.encode(self.encoding))
                yield flen == read, lineno, line.rstrip('\r\n')

    def _readDocument(self):
        # 每次读取一行返回
        with open(self.fileName, 'r') as data:
            for done, lineno, line in self._process(data):
                # 判断源文件一行的字节数是否超出规定的每行字节数
                if self._isTooLong(line):
                    # 输出是哪一行的字节数超出
                    self._scribble(
                        "Warning: wrapping line %d in %s" %
                        (lineno, self.fileName))
                    # 将超出的那一行截取分次返回，用宽度控制右边距
                    while self._isTooLong(line):
                        currWidth, currIndex = self._countLineWidth(line)
                        yield done, line[:currIndex]
                        line = line[currIndex:]
                yield done, line
    
    def _countLineWidth(self, line):
        """
        返回字符串在宽度内的字符索引
        """
        lineStr = line[:self.charsPerLine]
        currWidth = 0
        currIndex = 0
        for c in lineStr:
            currCharWidth = self.canvas.stringWidth(
                    c, fontName=self.font, fontSize=self.fontSize)
            if self.fontWidth < currCharWidth:
                currWidth += int(currCharWidth / self.fontWidth)
            else:
                currWidth += 1
            currIndex += 1
            if currWidth >= self.charsPerLine:
                break;
        return currWidth, currIndex
        
    def _isTooLong(self, line):
        """
        判断文字宽度是否超长
        """
        currWidth = 0
        for c in line:
            currCharWidth = self.canvas.stringWidth(
                    c, fontName=self.font, fontSize=self.fontSize)
            if self.fontWidth < currCharWidth:
                currWidth += int(currCharWidth / self.fontWidth)
            else:
                currWidth += 1
            if currWidth > self.charsPerLine:
                return True
        return False
        
    def _newpage(self):
        textobject = self.canvas.beginText()
        # 设置字体，大小，行距
        textobject.setFont(self.font, self.fontSize, leading=self.leading)
        # 设置开始外边距（坐标原点为页面左下角）
        textobject.setTextOrigin(self.margins.left, self.top)
        # 设置字距
        textobject.setCharSpace(self.kerning)
        if self.pageNumbering:
            self.canvas.drawString(
                self.pageNumberPlacement[0],
                self.pageNumberPlacement[1],
                str(self.canvas.getPageNumber()))
        return textobject

    def _scribble(self, text):
        if self.verbose:
            sys.stderr.write(text + os.linesep)

    def generate(self, encoding):
        if encoding:
            self.encoding = encoding
        # 输出注释
        self._scribble(
            "Writing '%s' with %d characters per "
            "line and %d lines per page..." %
            (self.fileName, self.charsPerLine, self.linesPerPage)
        )
        pageno = self._generatePlain(self._readDocument())
        self._scribble("PDF document: %d pages" % pageno)

    def _generatePlain(self, data):
        pageno = 1
        lineno = 0
        page = self._newpage()
        for _, line in data:
            page.textLine(line)
            lineno += 1
            # 用行数控制底边距
            if lineno == self.linesPerPage:
                self.canvas.drawText(page)
                # 每加一个page都需要运行一次
                self.canvas.showPage()
                lineno = 0
                pageno += 1
                page = self._newpage()
        if lineno > 0:
            self.canvas.drawText(page)
        else:
            pageno -= 1
        self.canvas.save()
        return pageno

PDFCreator(sys.argv[1:], Margins(
    marginRight,
    marginLeft,
    marginTop,
    marginBottom)).generate(sys.argv[2] if len(sys.argv) == 3 else None)

    