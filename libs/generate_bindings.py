#!/usr/bin/env python3
#script to automatically generate ctypes python bindings for draw_pico
import enum
import re

#constants
debug_mode = True

#lexing
token_chars_multi = ['++','--','<=','>=','==','!=','&&','||','<<','>>','+=',
    '-=','*=','/=','%=','->','<<=','>>=','&=','|=','^=','...','::','//']
token_chars = ['+','-','*','/','%','<','>','!','&','|','~','^','=','?',':',
    '(',')','[',']','=',',','"','\'','{','}',';','.','\\','#']
digits = ['0','1','2','3','4','5','6','7','8','9']

#parsing
c_types = ['bool','char','short','int','long','long long','float','double',
    'void',]
std_types = ['std::size_t','std::string','std::map','std::vector','std::set',
    'std::unordered_map']
otherlib_types = [] #root, etc.
drawpico_types = ['Axis','NamedFunc','PlotOpt','PlotOptTypes::BottomType',
    'PlotOptTypes::YAxisType','PlotOptTypes::TitleType',
    'PlotOptTypes::StackType','PlotOptTypes::OverflowType']
all_types = c_types+std_types+otherlib_types+drawpico_types
type_prefix_tokens = ['const','volatile','unsigned','signed','restrict',
    'volatile','static','register','extern','thread_local','mutable']

#wrapping, everything else used as pointer and casted to void*
wrapper_c_types = {'void':'void', 'bool':'int', 'char':'char', 
    'short':'short', 'int':'int', 'long':'long', 'long long':'long', 
    'float':'float', 'double':'double', 'std::size_t':'unsigned int', 
    'std::string':'const char*', 'unsigned char':'unsigned char', 
    'unsigned short':'unsigned short', 'unsigned int':'unsigned int', 
    'unsigned long':'unsigned long', 'unsigned long long':'unsigned long'}
wrapper_py_types = {'void':'c_void', 'char':'c_char', 'short':'c_short', 
    'int':'c_int', 'long':'c_long', 'float':'c_float', 'double':'c_double', 
    'const char*':'c_char_p', 'unsigned char':'c_ubyte', 
    'unsigned short':'c_ushort', 'unsigned int':'c_uint', 
    'unsigned long':'c_ulong'}
python_types = {'bool':'bool', 'char':'str', 
    'short':'int', 'int':'int', 'long':'int', 'long long':'int', 
    'float':'float', 'double':'float', 'std::size_t':'int', 
    'std::string':'str', 'unsigned char':'int', 
    'unsigned short':'int', 'unsigned int':'int', 
    'unsigned long':'int', 'unsigned long long':'int',
    'std::set':'list', 'std::vector':'list'}
operator_names = {'operator+':'__add__','operator-':'__sub__',
    'operator*':'__mul__','operator/':'__truediv__','operator%':'__mod__',
    'operator^':'__xor__','operator&':'__and__','operator|':'__or__',
    'operator!':'__invert__','operator,':'operatorcomma',
    'operator=':'operatorequals','operator<':'__lt__','operator>':'__gt__',
    'operator<=':'__le__','operator>=':'__ge__',
    'operator++':'operatorplusplus','operator--':'operatorminusminus',
    'operator<<':'__lshift__','operator>>':'__rshift__','operator==':'__eq__',
    'operator!=':'__ne__','operator&&':'__and__','operator||':'__or__',
    'operator+=':'__iadd__','operator-=':'__isub__','operator*=':'__imul__',
    'operator/=':'__idiv__','operator%=':'__imod__','operator^=':'__ixor__',
    'operator&=':'__iand__','operator|=':'__ior__','operator<<=':'__ilshift__',
    'operator>>=':'__irshift__','operator[]':'operatorsquarebrackets',
    'operator()':'operatorparentheses','operator->':'operatorminusgreater',
    'operator->*':'operatorminusgreaterasterisk'}

#-----------------------------------------------------------------------------
#                                  utilities
#-----------------------------------------------------------------------------
def list_at_or_empty(target_list, idx):
  '''Returns element of target_list at index idx or []'''
  if idx > 0 and idx < len(target_list):
    return list_[idx]
  return []

def string_at_or_empty(string, idx):
  '''Returns char of string at index idx or empty string'''
  if idx > 0 and idx < len(string):
    return string[idx]
  return ''

def debug(message):
  if (debug_mode==True):
    print('DEBUG: ',end='')
    print(message)

def error(message):
  print('ERROR: ',end='')
  print(message)

#-----------------------------------------------------------------------------
#                                    lexer
#-----------------------------------------------------------------------------

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
    r'\+\+',r'--',r'<=',r'>=',r'==',r'!=',r'&&',r'\|\|',r'<<',r'>>',
    r'\+=',r'-=',r'\*=',r'/=',r'%=',r'->',r'<<=',r'>>=',r'&=',r'\|=',r'\^=',
    r'\.\.\.',r'//',r'\+',r'-',r'\*',r'/',r'%',r'<',r'>',r'!',r'&',r'\|',
    r'~',r'\^',r'=',r'\?',r':',r'\(',r'\)',r'\[',r'\]',r'\{',r'\}',r'=',
    r',',r'"','\'',r';',r'\.',r'\\',r'#', #special character(s)
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

#def tokenize_line(string):
#  '''Lexer that returns C++ tokenized list from string'''
#  string = string.replace('\n','')
#  tokenized_string = []
#  running_string = ''
#  char_idx = 0
#  in_char_literal = False
#  in_string_literal = False
#  while char_idx < len(string):
#    char = string[char_idx]
#    if (char==' ' and not in_char_literal and not in_string_literal):
#      #end of a token, append to token list
#      if (running_string != ''):
#        tokenized_string.append(running_string)
#        running_string = ''
#    elif char in token_chars:
#      if in_char_literal:
#        if (char=='\''):
#          is_escaped = False
#          if (len(running_string)==2):
#            if (running_string[-1]=='\\'):
#              #char is '\'', not the end
#              is_escaped = True
#          if not is_escaped:
#            running_string += char
#            tokenized_string.append(running_string)
#            running_string = ''
#            in_char_literal = False
#      elif in_string_literal:
#        if (char=='\"'):
#          is_escaped = False
#          str_idx = 0
#          while str_idx < len(running_string):
#            if (running_string[str_idx] == '\\'):
#              if (str_idx == len(running_string)-1):
#                is_escaped = True
#              str_idx += 2
#            str_idx += 1
#          if not is_escaped:
#            running_string += char
#            tokenized_string.append(running_string)
#            running_string = ''
#            in_string_literal = False
#      else:
#        found_multichar_token = False
#        if (char_idx!=(len(string)-2)):
#          if (string[char_idx:char_idx+3] in token_chars_multi):
#            tokenized_string.append(running_string)
#            tokenized_string.append(string[char_idx:char_idx+3])
#            running_string = ''
#            char_idx += 2
#            found_multichar_token = True
#        if (not found_multichar_token and (char_idx!=(len(string)-1))):
#          if (string[char_idx:char_idx+2] in token_chars_multi):
#            if (string[char_idx:char_idx+2] == '::'):
#              running_string += '::'
#              char_idx += 1
#              found_multichar_token = True
#            elif (string[char_idx:char_idx+2] == '//'):
#              tokenized_string.append(running_string)
#              running_string = ''
#              found_multichar_token = True
#              char_idx = len(string) #skip rest
#            else:
#              tokenized_string.append(running_string)
#              tokenized_string.append(string[char_idx:char_idx+2])
#              running_string = ''
#              char_idx += 1
#              found_multichar_token = True
#        if not found_multichar_token:
#          if (char=='\''):
#            tokenized_string.append(running_string)
#            running_string = char
#            in_char_literal = True
#          elif (char=='\"'):
#            tokenized_string.append(running_string)
#            running_string = char
#            in_string_literal = True
#          else:
#            tokenized_string.append(running_string)
#            tokenized_string.append(char)
#            running_string = ''
#    else:
#      running_string += char
#    char_idx += 1
#  tokenized_string.append(running_string)
#  #resolve numeric literals ((-)?\d+(.)?\d+(e(-|+)?d+)?), but leave ambiguous -
#  #. and - are special tokens, e is not
#  tokenized_string = [i for i in tokenized_string if i != '']
#  token_idx = 0
#  while token_idx < len(tokenized_string):
#    if tokenized_string[token_idx][0] in digits:
#      if (list_at_or_empty(tokenized_string, token_idx+1)=='.'):
#        two_tokens_ahead = list_at_or_empty(tokenized_string, token_idx+2)
#        if (len(two_tokens_ahead)>0):
#          if (two_tokens_ahead[0] in digits):
#            if (tokenized_string[token_idx+2][-1]=='e'):
#              #to have been split, the next token must be - or +
#              tokenized_string = (tokenized_string[0:token_idx] + 
#                  [''.join(tokenized_string[token_idx:token_idx+5])] + 
#                  tokenized_string[token_idx+5:])
#            else: #not scientific
#              tokenized_string = (tokenized_string[0:token_idx] + 
#                  [''.join(tokenized_string[token_idx:token_idx+3])] + 
#                  tokenized_string[token_idx+3:])
#          else: #token two ahead isn't numeric
#            tokenized_string = (tokenized_string[0:token_idx] + 
#                [tokenized_string[token_idx]+ tokenized_string[token_idx+1]] + 
#                tokenized_string[token_idx+2:])
#        else: #no token two tokens ahead
#          tokenized_string = (tokenized_string[0:token_idx] + 
#              [tokenized_string[token_idx]+ tokenized_string[token_idx+1]] + 
#              tokenized_string[token_idx+2:])
#    token_idx += 1
#  return tokenized_string
#
#def tokenize_file(filename):
#  #all_tokens = []
#  #with open(filename) as header_file:
#  #  for line in header_file:
#  #    if (line[0]=='#'):
#  #      #skip preprocessor lines
#  #      continue
#  #    tokenized_line = tokenize_line(line)
#  #    all_tokens += tokenized_line
#  #debug(all_tokens)
#  #return all_tokens
#  header_file = open(filename,'r')
#  tokens = tokenize_cpp(header_file.read())
#  header_file.close()
#  return tokens

#-----------------------------------------------------------------------------
#                                 parser
#-----------------------------------------------------------------------------
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


#class Parser:
#  '''Class implementing basic C++ parser'''
#
#  def __init__(self, tokens):
#    '''Initializes parser from tokens'''
#    self.tokens = tokens
#    self.position = 0
#
#  def get_token(self):
#    '''returns current token'''
#    return self.tokens[self.position]
#
#  def next_token(self, skip=1):
#    '''continues to a subsequent token'''
#    self.position += skip
#
#  def get_next_token(self):
#    '''continues to next token and returns it'''
#    self.position += 1
#    return self.tokens[self.position]
#
#  def get_tokens_until(self, target):
#    '''return a list of tokens from the current token up to and including the 
#    first token matching target'''
#    token_list = []
#    while (self.get_token() != target):
#      token_list.append(self.get_token())
#      self.next_token()
#    token_list.append(self.get_token())
#    self.next_token()
#    return token_list
#
#  def end_of_tokens(self):
#    '''true if the end of tokens has been reached'''
#    return (self.position >= len(self.tokens))
#  
#  def eval(self):
#    '''Returns parsed tree from tokens'''
#    debug('eval, current token is '+self.get_token())
#    namespace_token = NamespaceToken()
#    namespace_token.name = 'global'
#    while not self.end_of_tokens():
#      member_namespace = self.eval_namespace()
#      if (member_namespace != None):
#        namespace_token.members.append(member_namepsace)
#      else:
#        member_class = self.eval_class()
#        if (member_class != None):
#          namespace_token.members.append(member_class)
#        else:
#          member_varfunc = self.eval_member()
#          if (member_varfunc != None):
#            namespace_token.members.append(member_varfunc)
#          else:
#            member_enum = self.eval_enum()
#            if (member_enum != None):
#              namespace_token.members.append(member_enum)
#    return namespace_token
#
#  def eval_namespace(self):
#    '''namespace identifier { namespace body }'''
#    debug('eval_namespace, current token is '+self.get_token())
#    if (self.get_token()=='namespace'):
#      namespace_token = NamespaceToken()
#      namespace_token.name = self.get_next_token()
#      self.next_token() #{
#      while (self.get_token() != '}'):
#        member_namespace = self.eval_namespace()
#        if (member_namespace != None):
#          namespace_token.members.append(member_namepsace)
#        member_class = self.eval_class()
#        if (member_class != None):
#          namespace_token.members.append(member_class)
#        member_varfunc = self.eval_member()
#        if (member_varfunc != None):
#          namespace_token.members.append(member_varfunc)
#        member_enum = self.eval_enum()
#        if (member_enum != None):
#          namespace_token.members.append(member_enum)
#      self.next_token() #}
#      return namespace_token
#    return None
#
#  def eval_enum(self):
#    '''enum (class)? identifier { (identifier (= literal)?,)+ }'''
#    if (self.get_token()=='enum'):
#      enum_tokens = self.get_tokens_until(';')
#      enum_string = ' '.join(enum_tokens)
#      enum_match = re.fullmatch((r'enum(?: class)? ([a-zA-Z_]\w*) \{ ([a-zA-Z'
#          r'_]\w*)(?: = (\d*))?(?: , ([a-zA-Z_]\w*)(?: = (\d*)))* ) ;'),
#          enum_string)
#      if (enum_match):
#        enum_match_groups = enum_match.groups()
#        match_idx = 0
#        grp_len = len(enum_match_groups)
#        while (match_idx < grp_len):
#          if (match_idx == 0):
#            enum_token.name = enum_match_groups[match_idx]
#          elif enum_match_groups[match_idx].isdigit():
#            enum_token.enum_values[grp_len] = enum_match_groups[match_idx]
#          else:
#            enum_token.enums.append(enum_match_groups[match_idx])
#            enum_token.enum_values.append('')
#          match_idx += 1
#      else:
#        debug('ERROR, no regex match for enum: '+enum_string)
#        exit()
#      #enum_token = EnumToken()
#      #debug('1 enum in token: '+self.get_token()) #TODO debug
#      #exit()
#      #self.next_token()
#      #if (self.get_token()=='class'):
#      #  self.next_token()
#      #enum_token.name = self.get_token()
#      #self.next_token()
#      #self.next_token() #{
#      #while (self.get_token() != '}'):
#      #  if (self.get_token()==','):
#      #    self.next_token()
#      #  debug('enum in token: '+self.get_token())
#      #  exit()
#      #  enum_token.enums.append(self.get_token())
#      #  self.next_token()
#      #  if (self.get_token()=='='):
#      #    self.next_token()
#      #    if (self.get_token()=='-'):
#      #      self.next_token()
#      #      enum_token.enum_values.push_back('-'+self.get_token())
#      #  elif (self.get_token()[0] in digits):
#      #    enum_token.enum_values.push_back(self.get_token())
#      #  else:
#      #    enum_token.enum_values.push_back('')
#      #self.next_token() #}
#      #self.next_token() #;
#      return enum_token
#    return None
#
#  def eval_class(self):
#    '''class identifier : (access identifier, )* { classbody };'''
#    debug('eval_class, current token is '+self.get_token())
#    if (self.get_token()=='class'):
#      class_token = ClassToken()
#      class_token.name = self.get_next_token()
#      members = [] 
#      members_access = []
#      current_access = 0
#      self.next_token()
#      while (self.get_token()!='{'):
#        class_token.parents_access.append(self.get_token())
#        class_token.parents.append(self.get_next_token())
#        self.next_token()
#        if (self.get_token()==','):
#          self.next_token()
#      self.next_token() #{, now inside class body
#      while (self.get_token()!='}'):
#        if (self.get_token()=='public'):
#          current_access = self.get_token()
#          self.next_token(2)
#        elif (self.get_token()=='protected'):
#          current_access = self.get_token()
#          self.next_token(2)
#        elif (self.get_token()=='private'):
#          current_access = self.get_token()
#          self.next_token(2)
#        else:
#          member_class = self.eval_class()
#          if (member_class != None):
#            members.append(member_class)
#            members_access.append(current_access)
#          member_varfunc = self.eval_member()
#          if (member_varfunc != None):
#            members.append(member_varfunc)
#            members_access.append(current_access)
#          member_enum = self.eval_enum()
#          if (member_enum != None):
#            members.append(member_enum)
#            members_access.append(current_access)
#      self.next_token(2) #} ;
#      class_token.members = members
#      class_token_access.members = members_access
#      return class_token
#    return None
#
#  def eval_expression(self, current_token=None):
#    '''continue until }, ,, or ;'''
#    debug('eval_expression, current token is '+self.get_token())
#    if (self.get_token() == ',' or self.get_token() == ';' or 
#        self.get_token() == '}' or self.get_token() == ')'):
#      return current_token
#    else:
#      if (self.get_token()[0]=='\"' and self.get_token()[-1]=='\"'):
#        expression_token = ExpressionToken()
#        expression_token.expression_type = ExpressionType.string_literal
#        expression_token.literal_value = self.get_token()
#        self.next_token()
#        return self.eval_expression(expression_token)
#      elif (self.get_token()[0]=='\'' and self.get_token()[-1]=='\''):
#        expression_token = ExpressionToken()
#        expression_token.expression_type = ExpressionType.char_literal
#        expression_token.literal_value = self.get_token()
#        self.next_token()
#        return self.eval_expression(expression_token)
#      elif (self.get_token()[0] in digits):
#        if (current_token != None):
#          if (current_token.expression_type == ExpressionType.numeric_literal):
#            if (current_token.literal_value=='-'):
#              current_token.literal_value = '-'+self.get_token()
#              return self.eval_expression(current_token)
#        expression_token = ExpressionToken()
#        expression_token.expression_type = ExpressionType.numeric_literal
#        expression_token.literal_value = self.get_token()
#        self.next_token()
#        return self.eval_expression(expression_token)
#      elif (self.get_token() == '-'):
#        if (current_token==None): #must be unary
#          expression_token = ExpressionToken()
#          expression_token.expression_type = ExpressionType.numeric_literal
#          expression_token.literal_value = self.get_token()
#          self.next_token()
#        #TODO: implement binary subtraction
#        expression_token = ExpressionToken()
#        expression_token.literal_value = self.get_token()
#        while (not (self.get_token() == ',' or self.get_token() == ';')):
#          self.next_token()
#        return expression_token
#      elif (self.get_token() == '{'):
#        expression_token = ExpressionToken()
#        expression_token.expression_type = ExpressionType.initializer_list
#        self.next_token()
#        while (self.get_token() != '}'):
#          if (sefl.get_token()!=','):
#            expression_token.subexpressions.append(self.eval_expression())
#          else:
#            coming_token = self.next_token()
#        self.next_token() #}
#        return self.eval_expression(expression_token)
#      else:
#        #bad/unimplemented expression
#        expression_token = ExpressionToken()
#        expression_token.literal_value = self.get_token()
#        while (not (self.get_token() == ',' or self.get_token() == ';')):
#          self.next_token()
#        return expression_token
#
#  def eval_function(self, function_name, function_type):
#    '''type+ identifier( (type identifier+ (= expression)+, )* ) const+ 
#    (= (default|delete)) (;|{functionbody}) '''
#    debug('eval_function, current token is '+self.get_token())
#    #eval_member handles up until the open parentheses
#    function_token = FunctionToken()
#    function_token.name = function_name
#    function_token.function_type = function_type
#    self.next_token() #(
#    while (self.get_token() != ')'):
#      arg_token = VariableToken()
#      arg_token.variable_type = self.eval_type()
#      if (arg_token.variable_type == None):
#        #error(' in function '+function_name+': bad argument type')
#        #assume this is a parentheses initializer for a variable
#        self.position -= 1 #back to (
#        return self.eval_variable(funciton_name, function_type)
#      if (self.get_token() != '=' and self.get_token() != ',' 
#          and self.get_token() != ')'):
#        arg_token.name = self.get_token()
#        self.next_token()
#      if (self.get_token() == '='):
#        self.next_token()
#        arg_token.variable_default = self.eval_expression()
#      function_token.args.append(arg_token)
#      if (self.get_token() != ',' and self.get_token() != ')'):
#        error('parsing function '+function_name+': expected "," but got '
#            + self.get_token())
#      if (self.get_token() == ','):
#        self.next_token() 
#    self.next_token() #)
#    while (self.get_token() != '{' and self.get_token() != ';'):
#      if (self.get_token()=='const'):
#        self.next_token()
#      elif (self.get_token()=='='):
#        default_str = self.get_next_token()
#        if (default_str == 'default' or default_str == 'delete'):
#          function_token.is_default = True
#          self.next_token() #default/delete
#        else:
#          error('expected default or delete, but got '+self.get_token())
#          self.next_token()
#      else:
#        error('parsing function '+function_name
#            +', unexpected postfix '+self.get_token())
#        self.next_token()
#    if (self.get_token() == '{'): 
#      bracket_count = 0
#      self.next_token()
#      while (not (self.get_token() == '}' and bracket_count == 0)):
#        if (self.get_token() == '{'):
#          bracket_count += 1
#        elif (self.get_token() == '}'):
#          bracket_count -= 1
#        self.next_token()
#      self.next_token() #}
#    else:
#      self.next_token() #;
#    return function_token
#
#  def eval_variable(self, variable_name, variable_type):
#    '''type name (= expression)+; 
#    eval_member handles up until name'''
#    debug('eval_variable, current token is '+self.get_token())
#    variable_token = VariableToken()
#    variable_token.name = variable_name
#    variable_token.variable_type = variable_type
#    while (self.get_token() != ';'):
#      if (self.get_token() == '='):
#        self.next_token() #=
#        variable_token.default = self.eval_expression()
#      elif (self.get_token() == '('):
#        self.next_token() #(
#        variable_token.default = self.eval_expression()
#        self.next_token() #)
#      else:
#        error('unexpected token '+self.get_token()+' in variable')
#        self.next_token()
#    self.next_token()
#    return variable_token
#
#  def eval_member(self):
#    '''function or variable (outside function) type+ identifier...'''
#    debug('eval_member, current token is '+self.get_token())
#    member_type = self.eval_type()
#    if (member_type != None):
#      member_name = self.get_token()
#      if (member_name=='('):
#        #constructor
#        member_name = '__init__'
#        return self.eval_function(member_name, member_type)
#      elif (member_name=='operator'):
#        member_name += self.get_next_token()
#        self.next_token() #operator symbol
#        return self.eval_function(member_name, member_type)
#      else:
#        self.next_token()
#        if (self.get_token()=='('):
#          return self.eval_function(member_name, member_type)
#        else:
#          return self.eval_variable(member_name, member_type)
#    else:
#      if (self.get_token()=='~'):
#        #destructor
#        member_type = TypeToken()
#        member_type.base_type = 'void'
#        member_name = '__del__'
#        self.next_token() #~
#        self.next_token() #class name
#        return self.eval_function(member_name, member_type)
#    return None
#
#  def eval_type(self, current_type_token=None):
#    '''(cv_qualifier)+ (storage_qualifier)+ (unsigned|signed|long|short)+ 
#    typename(<typename>)+ (*)* (&|&&)+ '''
#    debug(' eval_type, current token is '+self.get_token())
#    if self.get_token() in type_prefix_tokens:
#      if (current_type_token==None):
#        current_type_token = TypeToken()
#      prefix = self.get_token()
#      #don't need all the cv and storage class for now
#      if (prefix=='unsigned'):
#        current_type_token.signed = 'unsigned'
#      elif (prefix=='signed'):
#        current_type_token.signed = ''
#      elif (prefix=='const'):
#        current_type_token.cv_qualifier = 'const'
#      self.next_token() 
#      return self.eval_type(current_type_token) 
#    if self.get_token() in all_types:
#      if (current_type_token==None):
#        current_type_token = TypeToken()
#      type_name = self.get_token()
#      if (current_type_token.base_type == 'long'):
#        if (type_name=='long'):
#          current_type_token.base_type = 'long long'
#          self.next_token() 
#          return self.eval_type(current_type_token) 
#        elif (type_name=='double'):
#          current_type_token.base_type = 'double'
#          self.next_token() 
#          return self.eval_type(current_type_token) 
#        elif (type_name=='int'):
#          self.next_token() 
#          return self.eval_type(current_type_token) 
#        else:
#          current_type_token.base_type = type_name
#          self.next_token() 
#          return self.eval_type(current_type_token) 
#      elif (current_type_token.base_type == 'short'):
#        if (type_name=='int'):
#          self.next_token() 
#          return self.eval_type(current_type_token) 
#        else:
#          current_type_token.base_type = type_name
#          self.next_token() 
#          return self.eval_type(current_type_token) 
#      current_type_token.base_type = type_name
#      self.next_token() 
#      return self.eval_type(current_type_token) 
#    if (current_type_token!=None):
#      if (self.get_token() == '*'):
#        new_type_token = TypeToken()
#        new_type_token.base_type = 'pointer'
#        new_type_token.templates = [current_type_token]
#        self.next_token() 
#        return self.eval_type(new_type_token) 
#      if (self.get_token() == '&'):
#        self.next_token() 
#        return self.eval_type(current_type_token) 
#      if (self.get_token() == '&&'):
#        self.next_token() 
#        return self.eval_type(current_type_token) 
#      if (self.get_token() == '<'):
#        self.next_token()
#        template_type_token = self.eval_type()
#        current_type_token.templates.append(template_type_token)
#        template_div_token = self.get_token()
#        while (template_div_token==','):
#          self.next_token()
#          template_type_token = self.eval_type()
#          current_type_token.templates.append(template_type_token)
#          template_div_token = self.get_next_token()
#        if (template_div_token != '>'):
#          error('parsing type: expected ">" but got '+template_div_token)
#        self.next_token() #> 
#        return self.eval_type(current_type_token)
#    return current_type_token

##-----------------------------------------------------------------------------
##                            wrapper generation
##-----------------------------------------------------------------------------

def get_cpp_type(type_token):
  type_string = ''
  if (type_token.base_type=='pointer'):
    type_string += get_cpp_type(type_token.templates[0])
    type_string += '*'
    if (type_token.cv_qualifier=='const'):
      type_string += ' const'
  else:
    if (type_token.cv_qualifier=='const'):
      type_string += 'const '
    if (type_token.signed=='unsigned'):
      type_string += 'unsigned '
    type_string += type_token.base_type
    if (len(type_token.templates)>0):
      type_string += '<'
      first_template = False
      for template_token in type_token.templates:
        if first_template:
          first_template = False
        else:
          type_string += ', '
        type_string += type_from_token(template_token)
      type_string += '>'
  return type_string

def get_py_type(type_token):
  base_type = type_token.base_type
  if (base_type in python_types):
    return python_types[base_type]
  elif (base_type in drawpico_types):
    return base_type
  else:
    return 'None'

def get_c_type(type_token):
  if len(type_token.templates)==0:
    base_type = type_token.base_type
    if (type_token.signed == 'unsigned'):
      base_type += 'unsigned '
    if (base_type in wrapper_c_types):
      return wrapper_c_types[base_type]
    else:
      return 'void*'
  else:
    base_type = type_token.base_type
    if (base_type == 'pointer'):
      if (type_token.templates[0].base_type=='char'):
        if (type_token.cv_qualifier=='const'):
          return 'const char*'
        return 'char*'
      elif (type_token.templates[0].base_type in wrapper_c_types):
        return wrapper_c_types[type_token.templates[0].base_type]+'*'
    elif (base_type == 'std::set' or base_type == 'std::vector'):
      base_type = type_token.templates[0].base_type
      if (type_token.templates[0].signed == 'unsigned'):
        base_type += 'unsigned '
      if (base_type in wrapper_c_types):
        return wrapper_c_types[base_type]+'*'
      else:
        return 'void*'
    else:
      return 'void*'

def get_pyc_type(type_token):
  if len(type_token.templates)==0:
    base_type = type_token.base_type
    if (type_token.signed == 'unsigned'):
      base_type += 'unsigned '
    if (base_type in wrapper_c_types):
      return 'ctypes.'+wrapper_py_types[wrapper_c_types[base_type]]
    else:
      return 'ctypes.c_void_p'
  else:
    base_type = type_token.base_type
    if (base_type == 'pointer'):
      if (type_token.templates[0].base_type=='char'):
        return 'ctypes.c_char_p'
      elif (type_token.templates[0].base_type in wrapper_c_types):
        return ('ctypes.POINTER(ctypes.'+wrapper_py_types[wrapper_c_types[
            type_token.templates[0].base_type]]+')')
      else:
        return 'ctypes.c_void_p'
    elif (base_type == 'std::set' or base_type == 'std::vector'):
      base_type = type_token.templates[0].base_type
      if (type_token.templates[0].signed == 'unsigned'):
        base_type += 'unsigned '
      if (base_type in wrapper_c_types):
        return ('ctypes.POINTER(ctypes.'+wrapper_py_types[
            wrapper_c_types[base_type]]+')')
      else:
        return 'ctypes.c_void_p'
    else:
      return 'ctypes.c_void_p'

def clean_operators(string):
  if string in operator_names:
    return operator_names[string]
  return string

def write_c_wrappers(token, vector_type_wrappers=set(), 
    parent_hierarchy=[], used_function_names=set()):
  '''function that recurses through tokens and writes c function wrappers'''
  ret_string = ''
  if (token.token_type == TokenType.cpp_namespace):
    if (token.name != 'global'):
      parent_hierarchy.append((token.name, 'namespace'))
    for member_token in token.members:
      ret_string += write_c_wrappers(member_token, vector_type_wrappers, 
          parent_hierarchy, used_function_names)
    if (token.name != 'global'):
      parent_hierarchy.pop()
  elif (token.token_type == TokenType.cpp_class):
    parent_hierarchy.append((token.name, 'class'))
    ret_string += write_c_pointer_constructor(parent_hierarchy, 
        used_function_names)
    ret_string += '\n'
    member_idx = 0
    for member_token in token.members:
      if (token.members_access[member_idx] == 'public'):
        ret_string += write_c_wrappers(member_token, vector_type_wrappers,
            parent_hierarchy, used_function_names)
      member_idx += 1
    parent_hierarchy.pop()
  elif (token.token_type == TokenType.cpp_function):
    if ((not token.is_default) and (not token.name=='operator=')):
      ret_string += write_c_function_wrapper(token, vector_type_wrappers,
          parent_hierarchy, used_function_names)
      ret_string += '\n'
  elif (token.token_type == TokenType.cpp_variable):
    #variable wrapper one day?
    pass
  return ret_string

def expression_to_python(expression_token):
  if (expression_token.expression_type == ExpressionType.numeric_literal):
    return '='+expression_token.literal_value
  elif (expression_token.expression_type == ExpressionType.char_literal):
    return '=\''+expression_token.literal_value+'\''
  elif (expression_token.expression_type == ExpressionType.string_literal):
    return '=\''+expression_token.literal_value+'\''
  elif (expression_token.expression_type == ExpressionType.initializer_list):
    bracket_inner = ''
    first = True
    for subexpression_token in expression_token.subexpressions:
      if first:
        first = False
      else:
        bracket_inner += ','
      bracket_inner += expression_to_python(subexpression_token)
    return '=['+bracket_inner+']'
  return ''

def write_py_wrappers(token, parent_hierarchy=[], used_function_names=set()):
  '''function that recurses through tokens and writes Python wrappers'''
  #make two passes, the first is for marking overloads/duplicates
  ret_string = ''
  if (token.token_type == TokenType.cpp_namespace):
    if (token.name != 'global'):
      parent_hierarchy.append((token.name, 'namespace'))
    for member_token in token.members:
      ret_string += write_py_wrappers(member_token, parent_hierarchy)
    if (token.name != 'global'):
      parent_hierarchy.pop()
  elif (token.token_type == TokenType.cpp_class):
    parent_hierarchy.append((token.name, 'class'))
    #write overloaded functions
    all_function_name_set = set()
    all_function_name_set.add('__init__') #always ol constructor
    ovl_function_name_set = set()
    overloaded_functions = dict()
    overload_number = dict()
    member_idx = 0
    for function_token in token.members:
      if (token.members_access[member_idx] == 'public'):
        if function_token.token_type == TokenType.cpp_function:
          if not function_token.is_default:
            if function_token.name in all_function_name_set:
              ovl_function_name_set.add(function_token.name)
            else:
              all_function_name_set.add(function_token.name)
      member_idx += 1
    member_idx = 0
    for function_token in token.members:
      if (token.members_access[member_idx] == 'public'):
        if function_token.token_type == TokenType.cpp_function:
          if not function_token.is_default:
            fn_name = function_token.name
            if fn_name in ovl_function_name_set:
              if fn_name in overloaded_functions:
                overloaded_functions[fn_name].append(function_token)
              else:
                overloaded_functions[fn_name] = [function_token]
      member_idx += 1
    for ol_name in overloaded_functions:
      overload_number[ol_name] = 1
    #write ctypes type assignments
    pointer_init_token = FunctionToken()
    pointer_init_token.name = '__init__'
    pointer_init_token.function_type = TypeToken()
    pointer_init_token.function_type.base_type = token.name
    pointer_init_token.args.append(VariableToken())
    pointer_init_token.args[0].name = 'ptr'
    pointer_init_token.args[0].variable_type = TypeToken()
    pointer_init_token.args[0].variable_type.base_type = 'pointer'
    pointer_init_token.args[0].variable_type.templates.append(TypeToken())
    pointer_init_token.args[0].variable_type.templates[0].base_type = token.name
    overload_number['__init__'] = 2
    ret_string += write_ctypes_types(pointer_init_token, parent_hierarchy, 0)
    member_idx = 0
    for function_token in token.members:
      if (token.members_access[member_idx] == 'public'):
        if function_token.token_type == TokenType.cpp_function:
          if (function_token.is_default == False):
            duplicate_number = 0
            if function_token.name in overload_number:
              duplicate_number = overload_number[function_token.name]
              overload_number[function_token.name] += 1
            ret_string += write_ctypes_types(function_token, parent_hierarchy, 
            duplicate_number)
      member_idx += 1
    #class header
    ret_string += 'class '+token.name+':\n'
    #write overload disambiguators
    for ol_name, ol_functions in overloaded_functions.items():
      ret_string += write_overload_py_wrapper(ol_functions, parent_hierarchy)
      ret_string += '\n'
      overload_number[ol_name] = 1
    overload_number['__init__'] = 2
    #write normal functions
    member_idx = 0
    for function_token in token.members:
      if (token.members_access[member_idx] == 'public'):
        if function_token.token_type == TokenType.cpp_function:
          if not function_token.is_default:
            duplicate_number = 0
            if function_token.name in overload_number:
              duplicate_number = overload_number[function_token.name]
              overload_number[function_token.name] += 1
            ret_string += write_py_function_wrapper(function_token, 
                parent_hierarchy, duplicate_number)
            ret_string += '\n'
      member_idx += 1
    ret_string += '\n'
    parent_hierarchy.pop()
  #elif (token.token_type == TokenType.cpp_function):
  #  if ((not token.is_default) and (not token.name=='operator=')):
  #    ret_string += write_c_function_wrapper(token, vector_type_wrappers,
  #        parent_hierarchy, used_function_names)
  #    ret_string += '\n'
  #elif (token.token_type == TokenType.cpp_variable):
  #  #variable wrapper one day?
  #  pass
  return ret_string

def write_ctypes_types(function_token, parent_hierarchy, duplicate_number):
  hierarchy_name = ''
  parent_name = ''
  if (len(parent_hierarchy)>0):
    if (parent_hierarchy[-1][1]=='class'):
      parent_name = parent_hierarchy[-1][0]
    for hierarch in parent_hierarchy:
      hierarchy_name += hierarch[0]
  c_function_name = hierarchy_name+clean_operators(function_token.name)
  num_str = ''
  if (duplicate_number>1):
    num_str = str(duplicate_number)
  output_string = ('drawpico_bindings.'+c_function_name+num_str+'.argtypes = [')
  first_arg = True
  for arg in function_token.args:
    if first_arg:
      first_arg = False
    else:
      output_string += ', '
    output_string += get_pyc_type(arg.variable_type)
    if (arg.variable_type.base_type=='std::vector' or
        arg.variable_type.base_type=='std::set'):
      output_string += ', ctypes.c_uint'
  output_string += ']\n'
  output_string += ('drawpico_bindings.'+c_function_name+num_str+'.restype = ')
  output_string += (get_pyc_type(function_token.function_type)+'\n')
  return output_string

def write_overload_py_wrapper(function_tokens, parent_hierarchy):
  '''returns Python function to disambiguate between overloaded functions'''
  is_constructor = (function_tokens[0].name=='__init__')
  output_string = '  def '+function_tokens[0].name+'('
  parent_name = ''
  hierarchy_name = ''
  if (len(parent_hierarchy)>0):
    if (parent_hierarchy[-1][1]=='class'):
      parent_name = parent_hierarchy[-1][0]
    for hierarch in parent_hierarchy:
      hierarchy_name += hierarch[0]
  if (parent_name != ''):
    output_string += 'self, '
  output_string += '*args):\n' 
  function_index = 1
  if is_constructor:
    output_string += '    if(check_function_signature([(1,ctypes.c_void_p)],'
    output_string += '*args)):\n'
    output_string += '      self.wrapped_pointer_ = drawpico_bindings.'
    output_string += (hierarchy_name+'__init__(args[0])\n')
    output_string += '      return\n'
    output_string += '    if(check_function_signature([(1,'+parent_name+')],'
    output_string += '*args)):\n'
    output_string += '      self.wrapped_pointer_ = drawpico_bindings.'
    output_string += (hierarchy_name+'__init__(args[0].wrapped_pointer_)\n')
    output_string += '      return\n'
    function_index += 1
  for function_token in function_tokens:
    output_string += '    if(check_function_signature(['
    first_arg = True
    for arg in function_token.args:
      if first_arg:
        first_arg = False
      else:
        output_string += ','
      output_string += '('
      if (arg.default.token_type != TokenType.cpp_expression):
        output_string += '1,'
      else:
        output_string += '0,'
      output_string += get_py_type(arg.variable_type)
      output_string += ')'
    output_string += '],*args)):\n'
    output_string += ('      return self.'+function_token.name)
    output_string += (str(function_index)+'(*args)\n')
    function_index += 1
  output_string += '    raise AttributeError(\'Invalid arguments\')\n'
  return output_string

def write_py_function_wrapper(function_token, parent_hierarchy, 
    duplicate_number):
  '''returns Python function wrapper string to write to C wrapper file'''
  is_constructor = (function_token.name=='__init__')
  is_destructor = (function_token.name=='__del__')
  parent_class_name = ''
  hierarchy_name = ''
  if len(parent_hierarchy)>0:
    if (parent_hierarchy[-1][1]=='class'):
      for hierarch in parent_hierarchy[:-1]:
        parent_class_name = parent_hierarchy[-1][0]
    for hierarch in parent_hierarchy:
      hierarchy_name += hierarch[0]
  #write things that don't depend on arguments
  declare_string = ''
  casting_string = ''
  return_string = ''
  return_string_end = '\n'
  declare_string = '  def '+clean_operators(function_token.name)
  function_name_idx = ''
  if (duplicate_number>0):
    declare_string += str(duplicate_number)
  if (duplicate_number>1):
    function_name_idx = str(duplicate_number)
  declare_string += '('
  is_char_p = False
  #handle casting of result
  if (function_token.function_type.base_type == 'std::vector' or
    function_token.function_type.base_type == 'std::set'):
    drawpico_wrap_begin = ''
    drawpico_wrap_end = ''
    if (function_token.function_type.templates[0].base_type in drawpico_types):
      drawpico_wrap_begin = function_token.function_type.templates[0].base_type
      drawpico_wrap_begin += '('
      drawpico_wrap_end = ')'
    return_string = '    return_vec = drawpico_bindings.'
    return_string += (hierarchy_name+clean_operators(function_token.name))
    return_string += (function_name_idx+'(')
    cleaned_type = clean_cpp_type(get_cpp_type(
        function_token.function_type.templates[0]))
    return_string_end = '    return return_list\n'
    return_string_end = ('    drawpico_bindings.StdVector'+cleaned_type
        +'Delete(return_vec)\n'+return_string_end)
    return_string_end = ('      return_list.append'
        +'('+drawpico_wrap_begin+'drawpico_bindings.StdVector'+cleaned_type
        +'At(i)'+drawpico_wrap_end+')\n'
        +return_string_end)
    return_string_end = ('    for i in range(drawpico_bindings.StdVector'
        +cleaned_type+'Len(return_vec))\n'+return_string_end)
    return_string_end = '    return_list = []\n'+return_string_end
    return_string_end = ')\n'+return_string_end
  else:
    return_string = '    '
    drawpico_wrap_begin = ''
    drawpico_wrap_end = ''
    if (function_token.function_type.base_type in drawpico_types):
      drawpico_wrap_begin = function_token.function_type.base_type
      drawpico_wrap_begin += '('
      drawpico_wrap_end = ')'
    if is_constructor:
      return_string = '    self.wrapped_pointer_ = '
    elif (function_token.function_type.base_type != 'void'):
      return_string = '    return '
    return_string += (drawpico_wrap_begin+'drawpico_bindings.')
    return_string += (hierarchy_name+function_token.name+function_name_idx+'(')
    return_string_end = ')'+drawpico_wrap_end+'\n'
  first_arg = True
  if parent_class_name != '':
    declare_string += 'self'
    return_string += 'self.wrapped_pointer_'
    first_arg = False
  #now do argument processing
  for arg in function_token.args:
    if first_arg:
      first_arg = False
    else:
      declare_string += ', '
      return_string += ', '
    declare_string += arg.name
    arg_type = arg.variable_type
    if arg.default.token_type == TokenType.cpp_expression:
      declare_string += expression_to_python(arg.default)
    #handle casting 
    if (arg_type.base_type=='std::set' or arg_type.base_type=='std::vector'):
      template_type = arg_type.templates[0]
      unwrapped_str = ''
      if (template_type.base_type in drawpico_types):
        unwrapped_str = '_unwrapped_'
        casting_string += ('    '+arg.name+'_unwrapped_ = [i.wrapped_pointer_') 
        casting_string += ('for i in '+arg.name+']\n') 
      casting_string += ('    '+arg.name+'_casted_ = (')
      casting_string += (get_pyc_type(template_type)+' * len('+arg.name+'))(*')
      casting_string += (arg.name+unwrapped_str+')\n')
      return_string += (arg.name+'_casted_, len('+arg.name+')')
    elif (arg_type.base_type in drawpico_types):
      casting_string += ('    '+arg.name+'_casted_ = '+arg_type.base_type)
      casting_string += ('('+arg.name+')\n')
      return_string += (arg.name+'_casted_')
    else: #no casting string needed
      return_string += arg.name
  declare_string += ')\n'
  return (declare_string+casting_string+return_string+return_string_end)

def write_c_function_wrapper(function_token, vector_type_wrappers=set(),
    parent_hierarchy=[], used_function_names=set()):
  '''returns C++ function wrapper string to write to C wrapper file'''
  is_constructor = (function_token.name=='__init__')
  is_destructor = (function_token.name=='__del__')
  #get parent class name and hierarchy name, if relevant
  parent_class_name = ''
  parent_class_name_short = ''
  hierarchy_name = ''
  function_name = ''
  if len(parent_hierarchy)>0:
    if (parent_hierarchy[-1][1]=='class'):
      for hierarch in parent_hierarchy[:-1]:
        parent_class_name += (hierarch[0]+'::')
      parent_class_name += parent_hierarchy[-1][0]
      parent_class_name_short = parent_hierarchy[-1][0]
    for hierarch in parent_hierarchy[:-1]:
      hierarchy_name += hierarch[0]
  #write things that don't depend on arguments
  declare_string = '  '
  casting_string = ''
  return_string = ''
  return_string_end = '  }\n'
  c_type = get_c_type(function_token.function_type)
  if (function_token.function_type.base_type == 'std::string'):
    return_string = '    return ('
    return_string_end = ').c_str();\n'+return_string_end
    declare_string += (c_type+' ')
  elif (function_token.function_type.base_type == 'std::vector'):
    declare_string += 'void* '
    template_type = get_cpp_type(function_token.function_type.templates[0])
    template_type = template_type.replace('const ','')
    return_string = '    return static_cast<void*>('
    return_string += ' new(std::nothrow) std::vector<'
    return_string += (template_type+'>(')
    return_string_end = '));\n'+return_string_end
    vector_type_wrappers.add(function_token.function_type.templates[0])
  elif (function_token.function_type.base_type == 'std::set'):
    declare_string += 'void* '
    template_type = get_cpp_type(function_token.function_type.templates[0])
    template_type = template_type.replace('const ','')
    return_string = '    std::set<'+template_type+'> return_set = '
    return_string_end = ('    return static_cast<void*>(return_vec);\n'
        +return_string_end)
    return_string_end = ('    std::copy(return_set.begin(), return_set.end(),' 
        +'std::back_inserter(*return_vec));\n'+return_string_end)
    return_string_end = ('    return_vec->reserve(return_set.size());'
        +return_string_end)
    return_string_end = ('    std::vector<'+template_type
        +'>* return_vec = new(std::nothrow) std::vector<'+template_type+'>;\n'
        +return_string_end)
    return_string_end = ';\n'+return_string_end
    vector_type_wrappers.add(function_token.function_type.templates[0])
  elif (function_token.function_type.base_type != 'void'):
    declare_string += (c_type+' ')
    return_string = '    return static_cast<'
    return_string += c_type
    return_string += '>('
    return_string_end = ');\n'+return_string_end
  else:
    declare_string += (c_type+' ')
    return_string_end = ';\n'+return_string_end
  if is_constructor:
    return_string += 'new(std::nothrow) '
    return_string += parent_class_name
    return_string += '('
    return_string_end = ')'+return_string_end
    function_name = hierarchy_name+parent_class_name_short+'__init__'
  elif is_destructor:
    return_string = '    delete static_cast<'
    return_string += parent_class_name
    return_string += '*>(self);\n'
    return_string_end = ''
    function_name = hierarchy_name+parent_class_name_short+'__del__'
  else:
    if parent_class_name_short != '':
      return_string += 'static_cast<'
      return_string += parent_class_name
      return_string += '>(self)->'
      return_string += function_token.name
      return_string += '('
      return_string_end = ')'+return_string_end
      function_name = (hierarchy_name+parent_class_name_short
          +clean_operators(function_token.name))
    else:
      return_string += (function_token.name+'(')
      return_string_end = ')'+return_string_end
      function_name = (hierarchy_name+clean_operators(function_token.name))
  #avoid duplicate function names
  next_number = 1
  temp_function_name = function_name
  while temp_function_name in used_function_names:
    next_number += 1
    temp_function_name = function_name+str(next_number)
  function_name = temp_function_name
  used_function_names.add(function_name)
  #
  declare_string += function_name
  declare_string += '('
  first_arg = True
  first_return_arg = True
  if parent_class_name_short != '':
    if not is_constructor:
      declare_string += 'void* self'
      first_arg = False
  #now do argument processing
  for arg in function_token.args:
    if first_arg:
      first_arg = False
    else:
      declare_string += ', '
    if first_return_arg:
      first_return_arg = False
    else:
      return_string += ', '
    arg_c_type = get_c_type(arg.variable_type)
    declare_string += (arg_c_type + ' ' + arg.name)
    arg_type = arg.variable_type
    if (arg_type.base_type=='std::set' or arg_type.base_type=='std::vector'):
      declare_string += (', int ' + arg.name + '_len')
      template_cpp_type = get_cpp_type(arg_type.templates[0])
      vecset_type = 'vector'
      vecset_add = 'push_back'
      if (arg_type.base_type=='std::set'):
        vecset_type = 'set'
        vecset_add = 'insert'
      casting_string += ('    std::'+vecset_type+'<')
      casting_string += (template_cpp_type+'> '+arg.name+'_'+vecset_type+';\n')
      casting_string += ('    for (int i_=0; i_<'+arg.name+'_len; i_++) {\n')
      casting_string += ('      '+arg.name+'_'+vecset_type+'.'+vecset_add+'(')
      casting_string += (template_cpp_type+'(static_cast<'+template_cpp_type)
      casting_string += ('*>('+arg.name+')[i_]));\n')
      casting_string += ('    }\n')
      return_string += (arg.name+'_'+vecset_type)
    else: #no casting string needed
      if arg_type.base_type in wrapper_c_types:
        return_string += arg.name
      else:
        return_string += 'static_cast<'
        return_string += get_cpp_type(arg_type).replace('const ','')
        return_string += ('>('+arg.name+')')
  declare_string += ') {\n'
  return (declare_string+casting_string+return_string+return_string_end)

def write_c_pointer_constructor(parent_hierarchy=[], used_function_names=set()):
  #get parent class name and hierarchy name, if relevant
  parent_class_name = ''
  parent_class_name_short = ''
  hierarchy_name = ''
  function_name = ''
  if len(parent_hierarchy)>0:
    if (parent_hierarchy[-1][1]=='class'):
      for hierarch in parent_hierarchy[:-1]:
        parent_class_name += (hierarch[0]+'::')
      parent_class_name += parent_hierarchy[-1][0]
      parent_class_name_short = parent_hierarchy[-1][0]
    for hierarch in parent_hierarchy[:-1]:
      hierarchy_name += hierarch[0]
  #
  function_name = hierarchy_name+parent_class_name_short+'__init__'
  next_number = 1
  temp_function_name = function_name
  while temp_function_name in used_function_names:
    next_number += 1
    temp_function_name = function_name+str(next_number)
  function_name = temp_function_name
  used_function_names.add(function_name)
  #
  output_string = '  void* '
  output_string += (function_name+'(void * ptr) {\n')
  output_string += ('    return static_cast<void*>(new(std::nothrow) ')
  output_string += (parent_class_name+'(*ptr));\n')
  output_string += '  }\n'
  return output_string

def clean_cpp_type(string):
  return (string.replace('< ','').replace('> ','').replace(' ','')
      .replace('*','Ptr'))

def write_vector_type_wrappers(vector_type_wrappers):
  '''write C wrapper for vectors'''
  output_string = ''
  for type_token in vector_type_wrappers:
    c_type = get_c_type(type_token)
    cpp_type = get_cpp_type(type_token)
    #at function
    output_string += '  '+c_type+' StdVector'
    output_string += clean_cpp_type(cpp_type)
    output_string += 'At(void* vec_ptr, unsigned int pos) {\n'
    output_string += ('    return static_cast<'+c_type+'>(')
    if (c_type == 'void*'):
      output_string += '&('
    output_string += ('static_cast<std::vector<'+cpp_type+'>*>(vec_ptr)->at(pos)')
    if (c_type == 'void*'):
      output_string += ')'
    output_string += ');\n  }\n\n'
    #len function
    output_string += '  unsigned int StdVector'
    output_string += clean_cpp_type(cpp_type)
    output_string += 'Len(void* vec_ptr) {\n'
    output_string += ('    return (')
    output_string += ('static_cast<std::vector<'+cpp_type+'>*>(vec_ptr)->size()')
    output_string += ');\n  }\n\n'
    #delete function
    output_string += '  void StdVector'
    output_string += clean_cpp_type(cpp_type)
    output_string += 'Delete(void* vec_ptr) {\n'
    output_string += ('    delete (')
    output_string += ('static_cast<std::vector<'+cpp_type+'>*>(vec_ptr)')
    output_string += ');\n  }\n\n'
  return output_string

def output_cpp_file_header():
  ret_string = ''
  ret_string += '#include <algorithm>\n'
  ret_string += '#include <map>\n'
  ret_string += '#include <memory>\n'
  ret_string += '#include <new>\n'
  ret_string += '#include <set>\n'
  ret_string += '#include <unordered_map>\n'
  ret_string += '#include <vector>\n\n'
  ret_string += '#include "TError.h"\n\n'
  ret_string += '#include "core/axis.hpp"\n'
  ret_string += '#include "core/named_func.hpp"\n\n'
  ret_string += 'extern "C"\n{\n'
  ret_string += '  void SuppressRootWarnings() {\n'
  ret_string += '    gErrorIgnoreLevel = 6000;\n'
  ret_string += '  }\n\n'
  return ret_string

def output_cpp_file_tailer():
  return '}'

def output_py_file_header():
  ret_string = ''
  ret_string += '#ctypes drawpico bindings\n'
  ret_string += '#import ROOT #causes strange errors\n'
  ret_string += 'import ctypes\n\n'
  ret_string += 'drawpico_bindings = ctypes.cdll.LoadLibrary('
  ret_string += '\'libDrawPicoC.so\')\n'
  ret_string += 'drawpico_bindings.SuppressRootWarnings()\n\n'
  ret_string += 'def check_function_signature(arg_signature, *args):\n'
  ret_string += '  \'\'\'returns true if *args can match arg_signature\'\'\'\n'
  ret_string += '  for arg_idx in range(len(arg_signature)):\n'
  ret_string += '    if arg_idx > len(args):\n'
  ret_string += '      if arg_signature[arg_idx][0]==0: #optional\n'
  ret_string += '        continue\n'
  ret_string += '    if (arg_signature[arg_idx][1]==None):\n'
  ret_string += '      continue\n'
  ret_string += '    if (arg_signature[arg_idx][1]==int):\n'
  ret_string += '      if (type(args[arg_idx])==int\n'
  ret_string += '          or type(args[arg_idx])==float):\n'
  ret_string += '        continue\n'
  ret_string += '      else:\n'
  ret_string += '        return False\n'
  ret_string += '    elif (arg_signature[arg_idx][1]==float):\n'
  ret_string += '      if (type(args[arg_idx])==int\n'
  ret_string += '          or type(args[arg_idx])==float):\n'
  ret_string += '        continue\n'
  ret_string += '      else:\n'
  ret_string += '        return False\n'
  ret_string += '    else:\n'
  ret_string += '      if (type(args[arg_idx])==arg_signature[arg_idx][1]):\n'
  ret_string += '        continue\n'
  ret_string += '      else:\n'
  ret_string += '        return False\n'
  ret_string += '  return True\n\n'
  return ret_string

if __name__ == '__main__':
  #file_tokens = tokenize_file('inc/core/plot_opt.hpp')
  #parser = Parser(file_tokens)
  #tree = parser.eval()
  #traverse_token(tree)
  #vector_wrap_types = set()
  #cpp_output_file = open('example_drawpicoc.cxx','w')
  #cpp_output_file.write(output_cpp_file_header())
  #cpp_output_file.write(write_c_wrappers(tree,vector_wrap_types))
  #cpp_output_file.write(write_vector_type_wrappers(vector_wrap_types))
  #cpp_output_file.write(output_cpp_file_tailer())
  #cpp_output_file.close()
  #py_output_file = open('example___init__.py','w')
  #py_output_file.write(output_py_file_header())
  #py_output_file.write(write_py_wrappers(tree))
  #py_output_file.close()
  print(tokenize_file_cpp('inc/core/plot_opt.hpp'))

  
