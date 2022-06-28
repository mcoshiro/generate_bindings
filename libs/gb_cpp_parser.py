#!/usr/bin/env python3
#implements a basic C++ parser
from gb_utils import *
from gb_parser import Parser
import copy
import enum
import re

#constants
# operator overloading names
operator_names = {'+' : '__add__', '-' : '__sub__', '*' : '__mul__', 
    '/' : '__truediv__', '%' : '__mod__', '^' : '__xor__', 
    '&' : '__and__', '|' : '__or__', '~' : '__invert__',
    '=' : '__assign__', '<' : '__lt__', '>' : '__gt__', '+=' : '__addeq__',
    '-=' : '__subeq__', '*=' : '__muleq__', '/=' : '__diveq__',
    '%=' : '__modeq__', '^=' : '__xoreq__', '&=' : '__andeq__',
    '|=' : '__oreq__', '<<' : '__lshift__', '>>' : '__rshift__',
    '<<=' : '__lshifteq__', '>>=' : '__rshifteq', '==' : '__eq__',
    '!=' : '__ne__', '<=' : '__le__', '>=' : '__ge__', 
    '&&' : '__logicand__', '||' : '__logicor__', '++' : '__plusplus__',
    '--' : '__minusminus__', ',' : '__comma__', '->*' : '__arrowref__',
    '->' : '__arrow__', '()' : '__parentheses__', '[]' : '__brackets__',
    '!' : '__logicnot__'
    }

half_operator_names = {'(' : '__parentheses__', '[' : '__brackets__'
    } #split when tokenizing

#implement C++ tokens

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
    self.current_access = 'public' #access assigned to new members
    self.current_type = Token() #type assigned to new vars

class FunctionToken(Token):
  def __init__(self):
    self.name = ''
    self.function_type = Token() #type token
    self.args = [] #list of variable tokens
    self.is_default = False
    self.token_type = TokenType.cpp_function
    self.current_type = Token() #type assigned to new vars

class NamespaceToken(Token):
  def __init__(self):
    self.name = ''
    self.members = [] #list of tokens
    self.token_type = TokenType.cpp_namespace
    self.current_type = Token() #type assigned to new vars

class TypeToken(Token):
  def __init__(self):
    self.base_type = 'int' #default ex. signed
    self.signed = ''
    self.cv_qualifier = ''
    self.templates = [] #list of type tokens
    self.argtypes = [] #list of type tokens
    self.token_type = TokenType.cpp_type

class VariableToken(Token):
  def __init__(self):
    self.name = ''
    self.variable_type = Token() #type token
    self.default = Token() #expression token
    self.token_type = TokenType.cpp_variable

class ExpressionToken(Token):
  def __init__(self):
    self.subexpression = [] #list of expression tokens
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

def traverse_token(token):
  '''Debugging function that traverses a token tree with top-level token and 
  prints structure'''
  if (token.token_type == TokenType.cpp_class):
    print('class '+token.name)
    subtoken_idx = 0
    for subtoken in token.members:
      print(token.members_access[subtoken_idx],end=' ')
      traverse_token(subtoken)
      print(', ')
      subtoken_idx += 1
    print('] (end class '+token.name+')')
  elif (token.token_type == TokenType.cpp_enum):
    print('enum ', end='')
    if (token.is_enum_class):
      print('class ',end='')
    print('[', end='')
    for enum in token.enums:
      print(','+enum)
    print(']')
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
    if len(token.argtypes)>0:
      print('(',end='')
      for subtoken in token.argtypes:
        traverse_token(subtoken)
        print(',',end='')
      print(')',end='')
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

class CppParser(Parser):
  '''Class implementing a basic C++ parser'''

  def __init__(self, token_list):
    '''See Parser.__init__'''
    self.inner_parentheses = 0
    self.available_types = ['bool','char','short','int','long','long long',
        'float','double','void']
    Parser.__init__(self, token_list)

  def add_types(self, type_list):
    '''Add additional C++ types to be recognized'''
    self.available_types += type_list

  def exec_callback(self, py_token, param_name, param_value):
    '''Set parameter of token and return true, or return false if param_value
    incompatible with param_name'''
    if (param_name == 'accessmodifier'):
      if (param_value == 'public' or param_value == 'protected' 
          or param_value == 'private'):
        py_token.current_access = param_value
        return True
      return False
    elif (param_name == 'arg'):
      param_value.variable_type = py_token.current_type
      py_token.args.append(param_value)
      return True
    elif (param_name == 'argtype'):
      py_token.argtypes.append(param_value)
      return True
    elif (param_name == 'charliteral'):
      if (re.fullmatch('\'.*\'',param_value) != None):
        py_token.literal_value = param_value
        py_token.expression_type = ExpressionType.char_literal
        return True
      return False
    elif (param_name == 'constructor'):
      if (param_value in self.available_types):
        py_token.name = '__init__'
        init_type = TypeToken()
        init_type.variable_type = param_value
        py_token.function_type = init_type
        return True
      return False
    elif (param_name == 'cvqualifier'):
      if (param_value == 'const' or param_value == 'volatile'):
        py_token.cv_qualifier = param_value
        return True
      return False
    elif (param_name == 'default'):
      py_token.default = param_value
      return True
    elif (param_name == 'destructor'):
      if (param_value in self.available_types):
        py_token.name = '__del__'
        destructor_type = TypeToken()
        destructor_type.base_type = 'void'
        py_token.function_type = destructor_type
        return True
      return False
    elif (param_name == 'enum'):
      if (re.fullmatch(r'[a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*',param_value) != None):
        py_token.enums.append(param_value)
        py_token.enum_values.append('')
        return True
      return False
    elif (param_name == 'enumdefault'):
      py_token.enum_values[-1] = param_value
      return True
    elif (param_name == 'functionbody'):
      if (param_value != ';'):
        return True
      return False
    elif (param_name == 'functionconst'):
      if (param_value == 'const'):
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
      py_token.subexpression.append(param_value)
      py_token.expression_type = ExpressionType.initializer_list
      return True
    elif (param_name == 'isenumclass'):
      if (param_value == 'class'):
        py_token.is_enum_class = True
        return True
      return False
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
      if (py_token.token_type == TokenType.cpp_class):
        py_token.members_access.append(py_token.current_access)
      py_token.members.append(param_value)
      return True
    elif (param_name == 'membervar'):
      param_value.variable_type = py_token.current_type
      if (py_token.token_type == TokenType.cpp_class):
        py_token.members_access.append(py_token.current_access)
      py_token.members.append(param_value)
      return True
    elif (param_name == 'name'):
      if (re.fullmatch(r'[a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*',param_value) != None):
        py_token.name = param_value
        return True
      return False
    elif (param_name == 'namelessarg'):
      new_arg = VariableToken()
      new_arg.variable_type = param_value
      new_arg.name = '__nameless__'
      py_token.args.append(new_arg)
      return True
    elif (param_name == 'numericliteral'):
      if (re.fullmatch(r'\d+(?:\.\d*)?(?:e(?:\+\-)?\d+)?',param_value) != None):
        py_token.literal_value = param_value
        py_token.expression_type = ExpressionType.numeric_literal
        return True
      return False
    elif (param_name == 'operatorname'):
      if (param_value in operator_names):
        py_token.name = operator_names[param_value]
        return True
      elif (param_value in half_operator_names):
        py_token.name = half_operator_names[param_value]
        return True
      return False
    elif (param_name == 'operatornametwo'):
      if (py_token.name == '__parentheses__'):
        if (param_value == ')'):
          return True
      elif (py_token.name == '__brackets__'):
        if (param_value == ']'):
          return True
      elif (py_token.name == '__arrow__'):
        if (param_value == '*'):
          py_token.name = '__arrowref__'
          return True
      elif (py_token.name == '__gt__'):
        if (param_value == '>'):
          py_token.name = '__rshift__'
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
        new_py_token = copy.deepcopy(py_token)
        py_token.base_type = 'pointer'
        py_token.cv_qualifier = ''
        py_token.signed = ''
        py_token.templates = [new_py_token]
        py_token.argtypes = []
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
        py_token.literal_value = param_value
        py_token.expression_type = ExpressionType.string_literal
        return True
      return False
    elif (param_name == 'subtype'):
      if (param_value in self.available_types):
        new_py_token = copy.deepcopy(py_token)
        py_token.base_type = param_value
        py_token.cv_qualifier = ''
        py_token.signed = ''
        py_token.templates = [new_py_token]
        py_token.argtypes = []
        return True
      return False
    elif (param_name == 'template'):
      py_token.templates.append(param_value)
      return True
    elif (param_name == 'typealias'):
      if (re.fullmatch(r'[a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*',param_value) != None):
        self.available_types.append(param_value)
        return True
      return False
    elif (param_name == 'typename'):
      if (param_value in self.available_types):
        py_token.base_type = param_value
        return True
      return False
    elif (param_name == 'unknownexpression'):
      if (param_value == '('):
        self.inner_parentheses += 1
        return True
      if (param_value != ';'):
        if (param_value == ',' and self.inner_parentheses == 0):
          return False
        if (param_value == ')'):
          if (self.inner_parentheses == 0):
            return False
          else:
            self.inner_parentheses -= 1
        return True
      return False
    elif (param_name == 'usenamespace'):
      if (re.fullmatch(r'[a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)*',param_value) != None):
        for typename in self.available_types:
          if (re.fullmatch(param_value+'::.*',typename) != None):
            self.available_types.append(typename[(len(param_value)+2):])
        return True
      return False
    elif (param_name == 'usetype'):
      return True
    elif (param_name == 'vartype'):
      py_token.current_type = param_value
      return True
    elif (param_name == 'vertspecifier'):
      if (param_value == 'final' or param_value == 'override'):
        return True
      return False
    else:
      error('unknown parameter name '+param_name)
 
  def make_token_by_type(self, token_type):
    '''Returns a new token of token_type'''
    if (token_type == 'class'):
      return ClassToken()
    elif (token_type == 'enum'):
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
      return self.eval_token_regex_string(r'class <name> <vertspecifier> * '
          r'( : <parentaccess> '
          r'<parent> ( , <parentaccess> <parent> ) * ) ? \{ ( ( '
          r'<accessmodifier> : ) | ( [member:class] ; ) | ( '
          r'[member:function] <vertspecifier> * ; ) | '
          r'( [vartype:type] [membervar:variable] <vertspecifier> * ( , '
          r'[membervar:variable] <vertspecifier> * '
          r') * ; ) | ( [member:enum] ; ) | ( using <typealias> = '
          r'[usetype:type] ; ) | ( using namespace <usenamespace> ; ) ) * \}')
    elif (token_type == 'enum'):
      return self.eval_token_regex_string(r'enum <isenumclass> ? <name> \{ '
          r'<enum> ( = <enumdefault> ) ? ( , <enum> ( = <enumdefault> ) ? ) * '
          r'\}')
    elif (token_type == 'expression'):
      return self.eval_token_regex_string(r'<stringliteral> | <charliteral> | '
          r'<numericliteral> | ( \{ [initlist:expression] ? ( , '
          r'[initlist:expression] ) * \} )')
    elif (token_type == 'function'):
      return self.eval_token_regex_string(r'( [functiontype:type] operator '
          r'<operatorname> <operatornametwo> ? ) | ( [functiontype:type] '
          r'<name> ) | <constructor> | ( ~ <destructor> ) \( ( '
          r'( [vartype:type] [arg:variable] ) | [namelessarg:type] ( , '
          r'( [vartype:type] [arg:variable] ) | '
          r'[namelessarg:type] ) * ) ? \) <functionconst> ? ( = '
          r'<functiondefault> ) ? ( \{ <functionbody> * \} ) ?')
    elif (token_type == 'namespace'):
      return self.eval_token_regex_string(r'namespace <name> { ( '
          r'[member:namespace] | ( [member:class] ; ) | ( [member:function] ; ) '
          r'| ( [vartype:type] [membervar:variable] ( , [membervar:variable] ) '
          r'* ; ) | ( [member:enum] ; ) | ( using <typealias> = [usetype:type] ; '
          r') | ( using namespace <usenamespace> ; ) ) * }')
    elif (token_type == 'type'):
      return self.eval_token_regex_string(r'( ( <cvqualifier> | '
          r'<storagequalifier> | <signedqualifier> | <functiontypequalifier> '
          r') * ( ( short <shorttypename> ) | ( long <longtypename> ) | '
          r'<typename> ) ) | ( ( <cvqualifier> | <storagequalifier> | '
          r'<functiontypequalifier> ) * <signedqualifier> ) ( \< '
          r'[template:type] ( , [template:type] ) * \> ) ? '
          r'( : : [subtype:type] ) * '
          r'( \( [argtype:type] ( , [argtype:type] ) * \) ) ? <cvqualifier> '
          r'* <pointer> * <passqualifier> ?')
    elif (token_type == 'variable'):
      return self.eval_token_regex_string(r'<name> ( ( = '
          '[default:expression] | ( <unknownexpression> * ) ) | ( \( '
          r'[default:expression] | ( <unknownexpression> * ) \) ) ) ?')
    error('Invalid token type received.')
    return []

  def evaluate(self):
    global_token = NamespaceToken()
    global_token.name = 'Global'
    global_regex = self.eval_token_regex_string(r'( '
          r'[member:namespace] | ( [member:class] ; ) | ( [member:function] ; ) '
          r'| ( [vartype:type] [membervar:variable] ( , [membervar:variable] ) * '
          r'; ) | ( [member:enum] ; ) ) *')
    self.eval_parser(global_regex, global_token)
    return global_token

