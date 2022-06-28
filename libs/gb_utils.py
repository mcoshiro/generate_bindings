#!/usr/bin/env python3
#miscellaneous utilities for generate_bindings library

#constants
DEBUG_MODE = True

def list_at_or_empty(target_list, idx):
  '''Returns element of target_list at index idx or []'''
  if idx >= 0 and idx < len(target_list):
    return list_[idx]
  return []

def string_at_or_empty(string, idx):
  '''Returns char of string at index idx or empty string'''
  if idx >= 0 and idx < len(string):
    return string[idx]
  return ''

def debug(message):
  if (DEBUG_MODE==True):
    print('DEBUG: ',end='')
    print(message)

def error(message):
  print('ERROR: ',end='')
  print(message)

