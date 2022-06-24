#!/usr/bin/env python3
#script to automatically generate ctypes python bindings for draw_pico
from gb_utils import *
import enum
import re

#Allowed types - TODO allow for caller to determine
c_types = ['bool','char','short','int','long','long long','float','double',
    'void',]
std_types = ['std::size_t','std::string','std::map','std::vector','std::set',
    'std::unordered_map']
otherlib_types = [] #root, etc.
drawpico_types = ['Axis','NamedFunc','PlotOpt','PlotOptTypes::BottomType',
    'PlotOptTypes::YAxisType','PlotOptTypes::TitleType',
    'PlotOptTypes::StackType','PlotOptTypes::OverflowType']
all_types = c_types+std_types+otherlib_types+drawpico_types

#implement C++ entities TODO rename from "token"

class TokenType(enum.Enum):
  unparsed = 0
  cpp_type = 1
  cpp_class = 2
  cpp_namespace = 3
  cpp_function = 4
  cpp_variable = 5
  cpp_expression = 6
  cpp_enum = 7

class ExpressionType(enum.Enum):
  unimplemented = 0
  string_literal = 1
  initializer_list = 2
  numeric_literal = 3
  char_literal = 4

class Token:
  def __init__(self):
    self.token_type = TokenType.unparsed

class ClassToken(Token):
  def __init__(self):
    self.name = ''
    self.parents = []
    self.parents_access = []
    self.members = [] #list of tokens
    self.members_access = []
    self.token_type = TokenType.cpp_class
    self.current_access = 'public'

class FunctionToken(Token):
  def __init__(self):
    self.name = ''
    self.function_type = Token() #type token
    self.args = [] #list of variable tokens
    self.is_default = False
    self.token_type = TokenType.cpp_function

class NamespaceToken(Token):
  def __init__(self):
    self.name = ''
    self.members = [] #list of tokens
    self.token_type = TokenType.cpp_namespace

class TypeToken(Token):
  def __init__(self):
    self.base_type = ''
    self.signed = ''
    self.cv_qualifier = ''
    self.templates = [] #list of type tokens
    self.token_type = TokenType.cpp_type

class VariableToken(Token):
  def __init__(self):
    self.name = ''
    self.variable_type = Token() #type token
    self.default = Token() #expression token
    self.token_type = TokenType.cpp_variable

class ExpressionToken(Token):
  def __init__(self):
    self.subexpressions = [] #list of expression tokens
    self.literal_value = ''
    self.expression_type = ExpressionType.unimplemented
    self.token_type = TokenType.cpp_expression

class EnumToken(Token):
  def __init__(self):
    self.name = ''
    self.enums = []
    self.enum_values = []
    self.is_enum_class = False
    self.token_type = TokenType.cpp_enum

#for debugging
def traverse_token(token):
  '''Debugging function that traverses a token tree with top-level token and 
  prints structure'''
  if (token.token_type == TokenType.cpp_class):
    print('class '+token.name)
    subtoken_idx = 0
    for subtoken in token.members:
      print(token.members_access[subtoken_idx],end='')
      traverse_token(subtoken)
      print(', ')
      subtoken_idx += 1
    print('] (end class '+token.name+')')
  elif (token.token_type == TokenType.cpp_function):
    print('function '+token.name)
    print('type: ',end='')
    traverse_token(token.function_type)
    print(', args: [')
    for subtoken in token.args:
      traverse_token(subtoken)
      print(', ',end='')
    print(']')
  elif (token.token_type == TokenType.cpp_namespace):
    print('namespace '+token.name)
    print('members: [')
    for subtoken in token.members:
      traverse_token(subtoken)
      print(', ')
    print('] (end namespace '+token.name+')')
  elif (token.token_type == TokenType.cpp_type):
    if (token.signed == 'unsigned'):
      print('unsigned ',end='')
    print(token.base_type, end='')
    if len(token.templates)>0:
      print('<',end='')
      for subtoken in token.templates:
        traverse_token(subtoken)
        print(',',end='')
      print('>',end='')
  elif (token.token_type == TokenType.cpp_variable):
    print('variable ',end='')
    traverse_token(token.variable_type)
    print(' '+token.name,end='')
    if token.default.token_type == TokenType.cpp_expression:
      print(' = ',end='')
      traverse_token(token.default)
  elif (token.token_type == TokenType.cpp_expression):
    print(token.literal_value+'[',end='')
    for subtoken in token.subexpression:
      traverse_token(token.subexpression)
    print(']',end='')
  else:
    print('{unknown token}',end='')

class Parser:
  '''Class implementing skeleton of a basic parser'''

  def __init__(self, tokens):
    '''Initializes parser from tokens'''
    self.tokens = tokens
    self.position = 0

  def eval_token_regex_string(self, regex_string):
    '''Parses a token regex string. Space is treated as a token delimiter 
    unless escaped. <> are special characters that indicate a method should
    be called and the token at this location should be passed to the method. 
    [] are special characters that indicate another token regex should be
    inserted at this spot.
    Returns a python list of tuples representing the regex'''
    split_string = regex_string.split(' ')
    return eval_token_regex_split_string(split_string)

  def eval_token_regex_split_string(self, split_string):
    '''Same as eval_token_regex_string but after str.split is called'''
    regex_list = []
    token_idx = 0
    buffer_or = False
    while token_idx < len(split_string):
      if (split_string[token_idx]=='('):
        #beginning of block
        token_idx_2 = token_idx
        while split_string[token_idx_2] != ')':
          if (token_idx_2 == len(split_string)-1):
            error('Unmatched parentheses in parser regex')
          token_idx_2 += 1
        regex_list.append(
            ('block',eval_token_regex_split_string[token_idx+1,token_idx_2]))
        token_idx = token_idx_2
      elif (split_string[token_idx]=='?'):
        #optional
        regex_list = regex_list[:-1] + [('optional',[regex_list[-1]])]
      elif (split_string[token_idx]=='*'):
        #any
        regex_list = regex_list[:-1] + [('any',[regex_list[-1]])]
      elif (split_string[token_idx]=='+'):
        #express one or more as 1 + any
        regex_list = regex_list[] + [('any',[regex_list[-1]])]
      elif (split_string[token_idx]=='|'):
        #buffer or, continue from here since buffered or checks at end
        #after next token (group), or will be inserted
        buffer_or = True
        token_idx += 1
        continue 
      elif (string_at_or_empty(split_string[token_idx],0) == '<'):
        #method call
        method_string = split_string[token_idx]
        regex_list.append(('methodcall',method_string[1:-1]))
      elif (string_at_or_empty(split_string[token_idx],0) == '['):
        #subtoken
        method_string = split_string[token_idx]
        colon_idx = method_string.index(':')
        regex_list.append(('subtoken',method_string[1:colon_idx],method_string[colon_idx+1:-1]))
      else:
        #fixed name
        #add tuple ('fixedname', name)
        string_idx = 0
        name_string = split_string[token_idx]
        while string_idx < range(len(name_string)):
          if (name_string[string_idx]=='\\'):
            name_string = (name_string[0:string_idx]
                +name_string[string_idx+1:])
            string_idx += 1
          string_idx += 1
        regex_list.append(('fixedname',name_string))
      #if or is buffered, combine last two tokens
      if (buffer_or):
        regex_list = regex_list[:-2] + [('or',[regex_list[:-2]],[regex_list[:-1]])]
        buffer_or = False
      token_idx += 1
    return regex_list

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
    Returns 2 values, a status that is 1 if regex successfully matches, -1 if it
    fails, and tuple of (a list of setmethod calls, a list of setmethod values)
    '''
    #parser_regex = eval_token_regex_string('')
    #check if parser regex matches 
    original_pos = self.position
    params_to_set = []
    values_to_set = []
    regex_pos = 0
    while (regex_pos < len(regex_list)):
      current_regex = regex_list[regex_pos]
      if (current_regex[0]=='fixedname'):
        #assert token matches string
        if (self.tokens[self.position] != current_regex[1]):
          self.position = original_pos
          return -1, ([], [])
        else:
          regex_pos += 1
          self.position += 1
      elif (current_regex[0]=='methodcall'):
        #set py_token parameters based on token if we get to the end
        params_to_set.append(current_regex[1])
        values_to_set.append(self.tokens[token_pos])
        regex_pos += 1
        self.position += 1
      elif (current_regex[0]=='block'):
        #recurse one time
        status, params_inner = self.eval_parser(self, current_regex[1])
        if (status == -1):
          self.position = original_pos
          return -1, ([], [])
        params_to_set += params_inner[0]
        values_to_set += params_inner[1]
        regex_pos += 1
      elif (current_regex[0]=='subtoken'):
        #recurse one time
        subtoken_regex = self.get_regex_by_token_type(current_regex[2])
        new_token = self.make_token_by_type(current_regex[2])
        status, ntparams = self.eval_parser(self, subtoken_regex, new_token)
        if (status != -1):
          self.position = original_pos
          return -1, ([], [])
        params_to_set += params_inner[current_regex[1]]
        values_to_set += params_inner[new_token]
        regex_pos += 1
      elif (current_regex[0]=='optional'):
        #attempt to recurse one time
        status, params_inner = self.eval_parser(self, current_regex[1])
        if (status != -1):
          params_to_set += params_inner[0]
          values_to_set += params_inner[1]
        regex_pos += 1
      elif (current_regex[0]=='any'):
        #attempt to recurse until fail
        status = 1
        while (status != -1):
          status, params_inner = self.eval_parser(self, current_regex[1])
          if (status != -1):
            params_to_set += params_inner[0]
            values_to_set += params_inner[1]
        regex_pos += 1
      elif (current_regex[0]=='or'):
        #try two possible expressions
        status, params_inner = self.eval_parser(self, current_regex[1])
        if (status == -1):
          status, params_inner = self.eval_parser(self, current_regex[2])
          if (status == -1):
            self.position = original_pos
            return -1, ([], [])
        params_to_set += params_inner[0]
        values_to_set += params_inner[1]
        regex_pos += 1
      else:
        error('Unknown parser regex type encountered')
        regex_pos += 1
    #set parameters
    if (py_token != None):
      param_idx = 0
      while (param_idx < len(params_to_set)):
        valid = self.set_parameters(py_token, params_to_set[param_idx], 
            values_to_set[param_idx])
        if not valid:
          self.position = original_position
          return -1, ([], [])
        param_idx += 1
    return 1, (params_to_set, values_to_set)

class CppParser(Parser):
  '''Class implementing a basic C++ parser'''

  def set_parameters(self, py_token, param_name, param_value):
    '''Set parameter of token and return true, or return false if param_value
    incompatible with param_name'''
    if (param_name == 'accessmodifier'):
      py_token.current_access = param_value
      return True
    elif (param_name == 'arg'):
      py_token.args.append(param_value)
      return True
    elif (param_name == 'charliteral'):
      if (re.fullmatch('\'.*\'',param_value) != None):
        py_token.literalvalue = param_value
        py_token.expression_type = ExpressionType.char_literal
        return True
      return False
    elif (param_name == 'constructor'):
      py_token.name = '__init__'
      py_token.function_type = param_value
      return True
    elif (param_name == 'clmember'):
      py_token.members.append(param_value)
      py_token.members_access.append(py_token.current_access)
      return True
    elif (param_name == 'cvqualifier'):
      if (param_value == 'const' or param_value == 'volatile'):
        py_token.cv_qualifier = param_value
        return True
      return False
    elif (param_name == 'default'):
      py_token.default = param_value
      return True
    elif (param_name == 'destructor'):
      py_token.name = '__del__'
      py_token.function_type = 'void'
      return True
    elif (param_name == 'enum'):
      py_token.enums.append(param_value)
      py_token.enum_values.append('')
      return True
    elif (param_name == 'enumdefault'):
      py_token.enum_values[-1] = param_value
      return True
    elif (param_name == 'functionbody'):
      if (param_value != ';'):
        return True
      return False
    elif (param_name == 'functiondefault'):
      if (param_value == 'default' or param_value == 'delete'):
        py_token.is_default = True
        return True
      return False
    elif (param_name == 'functiontypequalifier'):
      if (param_value == 'inline' or param_value == 'virtual' or 
          param_value == 'explicit' or param_value == 'friend' or
          param_value == 'constexpr'):
        return True
      return False
    elif (param_name == 'functiontype'):
      py_token.function_type = param_value
      return True
    elif (param_name == 'initlist'):
      py_token.subtokens.append(param_value)
      py_token.expression_type = ExpressionType.initializer_list
      return True
    elif (param_name == 'isenumclass'):
      py_token.is_enum_class = True
      return True
    elif (param_name == 'longtypename'):
      if (param_value == 'int'):
        py_token.base_type = 'long'
        return True
      elif (param_value == 'long'):
        py_token.base_type = 'long long'
        return True
      elif (param_value == 'double'):
        py_token.base_type = 'long double'
        return True
      return False
    elif (param_name == 'member'):
      py_token.mambers.append(param_value)
      return True
    elif (param_name == 'name'):
      py_token.name = param_value
      return True
    elif (param_name == 'numericliteral'):
      if (re.fullmatch(r'\d+(?:\.\d*)?(?:e(?:\+\-)?\d+)?',param_value) != None):
        py_token.literalvalue = param_value
        py_token.expression_type = ExpressionType.numeric_literal
        return True
      return False
    elif (param_name == 'parentaccess'):
      py_token.parents_access.append(param_value)
      return True
    elif (param_name == 'parent'):
      py_token.parents.append(param_value)
      return True
    elif (param_name == 'passqualifier'):
      if (param_value == '&' or param_value == '&&'):
        return True
      return False
    elif (param_name == 'pointer'):
      if (param_value == '*'):
        new_py_token = TypeToken()
        new_py_token.base_type = 'pointer'
        new_py_token.templates = [py_token]
        py_token = new_py_token
        return True
      return False
    elif (param_name == 'signedqualifier'):
      if (param_value == 'signed'):
        return True
      if (param_value == 'unsigned'):
        py_token.signed = 'unsigned'
        return True
      return False
    elif (param_name == 'shorttypename'):
      if (param_value == 'int'):
        py_token.base_type = 'short'
        return True
      return False
    elif (param_name == 'storagequalifier'):
      if (param_value == 'static' or param_value == 'thread_local' or
          param_value == 'extern' or param_value == 'mutable'):
        return True
      return False
    elif (param_name == 'stringliteral'):
      if (re.fullmatch(r'".*"',param_value) != None):
        py_token.literalvalue = param_value
        py_token.expression_type = ExpressionType.string_literal
        return True
      return False
    elif (param_name == 'template'):
      py_token.templates.append(param_value)
      return True
    elif (param_name == 'typename'):
      if (param_value in all_types):
        py_token.base_type = param_value
        return True
      return False
    elif (param_name == 'variabletype'):
      py_token.variable_type = param_value
      return True
    else:
      error('unknown parameter name '+param_name)
 
  def make_token_by_type(self, token_type):
    '''Returns a new token of token_type'''
    if (token_type == 'class'):
      return ClassToken()
    else if (token_type == 'enum'):
      return EnumToken()
    elif (token_type == 'expression'):
      return ExpressionToken()
    elif (token_type == 'function'):
      return FunctionToken()
    elif (token_type == 'namespace'):
      return NamespaceToken()
    elif (token_type == 'variable'):
      return VariableToken()
    elif (token_type == 'type'):
      return TypeToken()
    error('Invalid token type received')
    return Token()

  def get_regex_by_token_type(self, token_type):
    '''method to get a regex list to interpret a C++ object from a name of a 
    token type.'''
    if (token_type == 'class'):
      return self.eval_token_regex_string(r'class <name> ( : <parentaccess> '
          r'<parent> ( , <parentaccess> <parent> ) * ) ? \{ ( ( '
          r'<accessmodifier> : ) | ( [clmember:class] ; ) | ( '
          r'[clmember:function] ; ) | '
          r'( [clmember:variable] ; ) | ( [clmember:enum] ; ) ) * \}')
    elif (token_type == 'enum'):
      return self.eval_token_regex_string(r'enum ( : <isenumclass> ) ? <name> \{ '
          r'<enum> ( = <enumdefault> ) ? ( , <enum> ? ( = <enumdefault> ) ) * '
          r'\}')
    elif (token_type == 'expression'):
      return self.eval_token_regex_string(r'<stringliteral> | <charliteral> | '
          r'<numericliteral> | ( \{ [initlist:expression] ? ( , '
          r'[initlist:expression] ) * \} )')
    elif (token_type == 'function'):
      return self.eval_token_regex_string(r'( [functiontype:type] <name> ) | '
          r'[constructor:type] | ( ~ [destructor:type] ) \( '
          r'[arg:variable] ( , [arg:variable] ) * \) <funcconst> ? ( = '
          r'<functiondefault> ) ? ( \{ <functionbody> * \} ) ?')
    elif (token_type == 'namespace'):
      return self.eval_token_regex_string(r'namespace <name> { ( '
          r'[member:namespace] | ( [member:class] ; ) | ( [member:function] ; ) '
          r'( [member:variable] ; ) | ( [member:enum] ; ) ) * }')
    elif (token_type == 'type'):
      return self.eval_token_regex_string(r'( <cvqualifier> | '
          r'<storagequalifier> | <signedqualifier> | <functiontypequalifier> '
          r') * (short <shorttypename> | long <longtypename> | <typename>) '
          r'\< [template:type] ( , [template:type] ) * \> <pointer> * '
          r'<passqualifier> ?')
    elif (token_type == 'variable'):
      return self.eval_token_regex_string(r'[variabletype:type] <name> ( = '
          '[default:expression] | \( [default:expression] \) )')
    error('Invalid token type received.')
    return []

  def eval(self):
    global_token = NamespaceToken
    global_token.Name = 'Global'
    global_regex = self.eval_token_regex_string(r'( '
          r'[member:namespace] | ( [member:class] ; ) | ( [member:function] ; ) '
          r'( [member:variable] ; ) | ( [member:enum] ; ) ) *')
    Parser.eval_parser(self, global_regex, global_token)
    return global_token

