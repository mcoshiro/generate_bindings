#!/usr/bin/env python3
#implements a basic extendable parser
from gb_utils import *
import enum
import re

class Parser:
  '''Class implementing skeleton of a basic parser'''

  def __init__(self, tokens):
    '''Initializes parser from tokens'''
    self.tokens = tokens
    self.position = 0

  def eval_token_regex_split_string(self, split_string):
    '''Same as eval_token_regex_string but after str.split is called'''
    regex_list = []
    token_idx = 0
    buffer_or = False
    while token_idx < len(split_string):
      if (split_string[token_idx]=='('):
        #beginning of block
        token_idx_2 = token_idx+1
        paren_depth = 0
        while not (split_string[token_idx_2] == ')' and paren_depth == 0):
          if (split_string[token_idx_2] == '('):
            paren_depth += 1
          elif (split_string[token_idx_2] == ')'):
            paren_depth -= 1
          if (token_idx_2 == len(split_string)-1):
            error('Unmatched parentheses in parser regex')
          token_idx_2 += 1
        regex_list.append(
            ('block',self.eval_token_regex_split_string(
            split_string[token_idx+1:token_idx_2])))
        token_idx = token_idx_2
      elif (split_string[token_idx]=='?'):
        #optional
        regex_list = regex_list[:-1] + [('optional',[regex_list[-1]])]
      elif (split_string[token_idx]=='*'):
        #any
        regex_list = regex_list[:-1] + [('any',[regex_list[-1]])]
      elif (split_string[token_idx]=='+'):
        #express one or more as 1 + any
        regex_list = regex_list + [('any',[regex_list[-1]])]
      elif (split_string[token_idx]=='|'):
        #buffer or, continue from here since buffered or checks at end
        #after next token (group), or will be inserted
        buffer_or = True
        token_idx += 1
        continue 
      elif (string_at_or_empty(split_string[token_idx],0) == '<'):
        #method call
        method_string = split_string[token_idx]
        regex_list.append(('callback',method_string[1:-1]))
      elif (string_at_or_empty(split_string[token_idx],0) == '['):
        #subtoken
        method_string = split_string[token_idx]
        colon_idx = method_string.index(':')
        regex_list.append(('subtoken',method_string[1:colon_idx],
            method_string[colon_idx+1:-1]))
      else:
        #fixed name
        #add tuple ('fixedname', name)
        string_idx = 0
        name_string = split_string[token_idx]
        while string_idx < len(name_string):
          if (name_string[string_idx]=='\\'):
            name_string = (name_string[0:string_idx]
                +name_string[string_idx+1:])
            string_idx += 1
          string_idx += 1
        regex_list.append(('fixedname',name_string))
      #if or is buffered, combine last two tokens
      if (buffer_or):
        regex_list = regex_list[:-2] + [('or',[regex_list[-2]],[regex_list[-1]])]
        buffer_or = False
      token_idx += 1
    return regex_list

  def eval_token_regex_string(self, regex_string):
    '''Parses a token regex string. Space is treated as a token delimiter 
    unless escaped. <> are special characters that indicate a method should
    be called and the token at this location should be passed to the method. 
    [] are special characters that indicate another token regex should be
    inserted at this spot.
    Returns a python list of tuples representing the regex'''
    split_string = regex_string.split(' ')
    return self.eval_token_regex_split_string(split_string)

  def get_regex_by_token_type(token_type):
    '''method to get a regex list from a name of a token type. To be extended
    in derived classes'''
    error('Invalid token type received.')
    return []

  def make_token_by_type(token_type):
    '''method to make a python token object from a name of a token type. To be 
    extended in derived classes'''
    error('Invalid token type received.')
    return None

  def eval_parser(self, regex_list, py_token=None):
    '''Evaluates tokens starting from current position, attempting to interpret
    them according to regex_list. If py_token is not none, any method calls
    encountered will be applied to that token.
    Returns true if able to successfully match regex_list and false otherwise.
    '''
    #parser_regex = eval_token_regex_string('')
    #check if parser regex matches 
    original_pos = self.position
    regex_pos = 0
    while (regex_pos < len(regex_list)):
      if (self.position >= len(self.tokens)):
        return False
      current_regex = regex_list[regex_pos]
      if (current_regex[0]=='fixedname'):
        #assert token matches string
        if (self.tokens[self.position] != current_regex[1]):
          self.position = original_pos
          return False
        else:
          regex_pos += 1
          self.position += 1
      elif (current_regex[0]=='callback'):
        #set py_token parameters based on token
        if (not self.exec_callback(py_token, current_regex[1], 
            self.tokens[self.position])):
          self.position = original_pos
          return False
        regex_pos += 1
        self.position += 1
      elif (current_regex[0]=='block'):
        #recurse one time
        if (not self.eval_parser(current_regex[1], py_token)):
          self.position = original_pos
          return False
        regex_pos += 1
      elif (current_regex[0]=='subtoken'):
        #recurse one time
        subtoken_regex = self.get_regex_by_token_type(current_regex[2])
        new_token = self.make_token_by_type(current_regex[2])
        if (not self.eval_parser(subtoken_regex, new_token)):
          self.position = original_pos
          return False
        self.exec_callback(py_token, current_regex[1], new_token)
        regex_pos += 1
      elif (current_regex[0]=='optional'):
        #attempt to recurse one time
        self.eval_parser(current_regex[1],py_token)
        regex_pos += 1
      elif (current_regex[0]=='any'):
        #attempt to recurse until fail
        status = 1
        while (self.eval_parser(current_regex[1],py_token)):
          pass
        regex_pos += 1
      elif (current_regex[0]=='or'):
        #try two possible expressions
        if (not self.eval_parser(current_regex[1],py_token)):
          if (not self.eval_parser(current_regex[2],py_token)):
            self.position = original_pos
            return False
        regex_pos += 1
      else:
        error('Unknown parser regex type encountered')
        regex_pos += 1
    #Successfully matched full regex
    return True

