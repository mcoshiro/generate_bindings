#!/usr/bin/env python3
#testing script for generate_bindings package
import gb_lexer
import gb_cpp_parser
import enum
import re

#types needed for DrawPico
std_types = ['const_iterator', 'std::function', 'std::map', 
    'std::ostream', 'std::set', 'std::shared_ptr',
    'std::size_t', 'std::string', 'std::unique_ptr', 'std::unordered_map', 
    'std::vector']
otherlib_types = ['TCanvas','TGraph','TGraphAsymmErrors','TH1D','TLatex','TLegend',
    'TLine','TPad','TString']
drawpico_types = ['Axis','Baby','DataSample','Figure','FigureComponent',
    'Hist1D','NamedFunc','Palette','PlotOpt','Process','ProcessList',
    'SampleLoader','SingleHist1D','Figure::FigureComponent',
    'NamedFunc::ScalarType','NamedFunc::VectorType',
    'NamedFunc::ScalarFunc','NamedFunc::VectorFunc',
    'PlotOptTypes::BottomType',
    'PlotOptTypes::YAxisType','PlotOptTypes::TitleType',
    'PlotOptTypes::StackType','PlotOptTypes::OverflowType','Process::Type']
all_types = std_types+otherlib_types+drawpico_types

if __name__ == '__main__':
  #print(gb_lexer.tokenize_file_cpp('../draw_pico/inc/core/axis.hpp'))
  #print('\n\n')
  #print(gb_lexer.tokenize_file_cpp('../draw_pico/inc/core/plot_opt.hpp'))
  #print('\n\n')
  #print(gb_lexer.tokenize_file_cpp('../draw_pico/inc/core/named_func.hpp'))
  #print('\n\n')
  my_tokens = gb_lexer.tokenize_file_cpp('../draw_pico/inc/core/plot_maker.hpp')
  my_parser = gb_cpp_parser.CppParser(my_tokens)
  my_parser.add_types(all_types)
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


  
