#!/usr/bin/env python3
#testing script for generate_bindings package
import gb_lexer
import gb_cpp_parser
import enum
import re

if __name__ == '__main__':
  #print(gb_lexer.tokenize_file_cpp('../draw_pico/inc/core/axis.hpp'))
  #print('\n\n')
  #print(gb_lexer.tokenize_file_cpp('../draw_pico/inc/core/plot_opt.hpp'))
  #print('\n\n')
  my_tokens = gb_lexer.tokenize_file_cpp('../draw_pico/inc/core/axis.hpp')
  my_parser = gb_cpp_parser.CppParser(my_tokens)
  print(my_parser.tokens)
  #print(my_parser.eval_token_regex_string(r'( test <name> ) | ( test2 <name> )'))
  #print('\n\n')
  #print(my_parser.eval_token_regex_string(r'( [functiontype:type] <name> ) | '
  #    r'[constructor:type] | ( ~ [destructor:type] ) \( ( '
  #    r'[arg:variable] ( , [arg:variable] ) * ) ? \) <funcconst> ? ( = '
  #    r'<functiondefault> ) ? ( \{ <functionbody> * \} ) ?'))
  #print('\n\n')
  #print(my_parser.eval_token_regex_string(r'class <name> ( : <parentaccess> '
  #    r'<parent> ( , <parentaccess> <parent> ) * ) ? \{ ( ( '
  #    r'<accessmodifier> : ) | ( [clmember:class] ; ) | ( '
  #    r'[clmember:function] ; ) | '
  #    r'( [clmember:variable] ; ) | ( [clmember:enum] ; ) ) * \}'))
  #print('\n\n')
  #print(my_parser.eval_token_regex_string(r'enum ( : <isenumclass> ) ? <name> \{ '
  #    r'<enum> ( = <enumdefault> ) ? ( , <enum> ? ( = <enumdefault> ) ) * '
  #    r'\}'))
  #print('\n\n')
  #print(my_parser.eval_token_regex_string(r'( <cvqualifier> | '
  #        r'<storagequalifier> | <signedqualifier> | <functiontypequalifier> '
  #        r') * (short <shorttypename> | long <longtypename> | <typename> ) '
  #        r'\< [template:type] ( , [template:type] ) * \> <pointer> * '
  #        r'<passqualifier> ?'))
  #print('\n\n')
  gb_cpp_parser.traverse_token(my_parser.evaluate())


  
