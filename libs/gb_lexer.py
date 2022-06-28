#!/usr/bin/env python3
#implements function for tokenizing C++ source
from gb_utils import *
import re

def compile_regex_list(regex_list):
  regex = '('
  for token_idx in range(len(regex_list)):
    if (token_idx != 0):
      regex += '|'
    regex += '(?:'+regex_list[token_idx]+')'
  regex += ')'
  return re.compile(regex)

#define regex constant
cpp_regex_list = [
    r'//.*\n', #line comment
    r'/\*[^\*]*(?:\*[^/][^\*]*)*\*/', #bulk comment
    r'#.*\n', #preprocessor directive
    r'"(?:[^"\\]*)(?:\\.[^"\\]*)*"', #string literal
    '\'(?:[^\\\\]|\\\\.)\'', #char literal
    r'\d+(?:\.\d*)?(?:e(?:\+\-)?\d+)?', #numeric literal
    r'\+\+',r'--',r'<=',r'>=',r'==',r'!=',r'&&',r'\|\|',r'<<',
    r'\+=',r'-=',r'\*=',r'/=',r'%=',r'->',r'<<=',r'>>=',r'&=',r'\|=',r'\^=',
    r'\.\.\.',r'//',r'\+',r'-',r'\*',r'/',r'%',r'<',r'>',r'!',r'&',r'\|',
    r'~',r'\^',r'=',r'\?',r':',r'\(',r'\)',r'\[',r'\]',r'\{',r'\}',r'=',
    r',',r'"','\'',r';',r'\.',r'\\',r'#', #special character(s), currently splitting >>
    r'[a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*'#name
    ]
cpp_regex = compile_regex_list(cpp_regex_list)

def tokenize_file_cpp(filename):
  '''Read file, split content into C++ tokens, and return list of tokens, omitting comments and preprocessor directives'''
  header_file = open(filename,'r')
  tokens = re.findall(cpp_regex, header_file.read())
  header_file.close()
  token_idx = 0
  token_remove_list = []
  while token_idx < len(tokens):
    if tokens[token_idx][0] == '#':
      token_remove_list.append(token_idx)
    elif len(tokens[token_idx]) > 1:
      if tokens[token_idx][0:2] == '//':
        token_remove_list.append(token_idx)
      elif tokens[token_idx][0:2] == '/*':
        token_remove_list.append(token_idx)
    token_idx += 1
  token_remove_list.reverse()
  for token_remove_idx in token_remove_list:
    tokens.pop(token_remove_idx)
  return tokens
