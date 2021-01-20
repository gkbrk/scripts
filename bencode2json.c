/* bencode2json - Utility to convert bencoded data to JSON data.
 *
 * Copyright (C) 2021, Gokberk Yaltirakli <opensource@gkbrk.com>
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice,
 *    this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/* Configuration */
#define MAX_INT_LEN 50

/* This tool uses only the following 3 functions for I/O. By default, the
   bencoded data is read from the stdin and JSON is produced on the stdout. This
   can be changed in the following functions, if it is needed to read/write data
   to other places.
*/

/* Reads one byte of bencoded input. */
static int get_character() {
  return getc(stdin);
}

/* Unreads one character of input.
 *
 * This function unreads a character and puts it back in the input stream. The
 * next call to get_character will return this value.
 *
 */
static void unget_character(char c) {
  ungetc(c, stdin);
}

/* Outputs a single character. */
static void output_character(char c) {
  putc(c, stdout);
}

/*
 * Converting an integer is easy as the JSON representation is the same as the
 * bencoded representation.
 */
static void convert_integer() {
  for (;;) {
    char c = get_character();

    if (c == 'e')
      break;
    else
      output_character(c);
  }
}

static void convert_value();

static void convert_list() {
  uint8_t output = 0;
  
  output_character('[');
  
  for (;;) {
    char c = get_character();

    if (c == 'e')
      break;

    unget_character(c);
    if (output)
      output_character(',');
    output = 1;
    convert_value();
  }
  
  output_character(']');
}

static void convert_dictionary() {
  uint8_t output = 0;

  output_character('{');

  for (;;) {
    char c = get_character();

    if (c == 'e')
      break;

    unget_character(c);
    if (output)
      output_character(',');

    output = 1;
    convert_value();
    output_character(':');
    convert_value();
  }

  output_character('}');
}

/* Reads the string length prefix and parses it as a number. */
static size_t read_count() {
  char lenBuf[MAX_INT_LEN];
  size_t lenBufLen = 0;

  for (;;) {
    char c = get_character();
    
    if (c == ':')
      break;
    
    lenBufLen++;
    lenBuf[lenBufLen - 1] = c;
    if (lenBufLen >= MAX_INT_LEN)
      break;
  }
  lenBuf[lenBufLen] = 0;
  
  return atoi(lenBuf);
}

static void convert_string() {
  /* count - The length of the string given by the length prefix. */
  /* byte[] - Used for Unicode escapes. */
  /* i - Loop index for the string characters. */
  size_t count = read_count();
  char byte[3];
  size_t i;
    
  output_character('"');
  
  for (i = 0; i < count; i++) {
    char c = get_character();

    if (c == '"' || c == '\\') {
      output_character('\\');
      output_character(c);
    } else if (isalnum(c) || ispunct(c) || c == ' ') {
      /* Alphanumeric characters, punctuation and space can be output without
         any escaping. */
      output_character(c);
    } else {
      /* On most decoders, this works for text data but not for binary data */
      output_character('\\');
      output_character('u');
      output_character('0');
      output_character('0');

      sprintf(byte, "%02x", (uint8_t)c);
      output_character(byte[0]);
      output_character(byte[1]);
    }
  }
  
  output_character('"');
}

/*
 * Read a bencoded value from the input and output the JSON equivalent.
 */
static void convert_value() {
  char c = get_character();

  /* Bencode datatype mapping:
   *
   * i - integer
   * l - list
   * d - dictionary
   * otherwise, it's a string */
  if (c == 'i')
    convert_integer();
  else if (c == 'l')
    convert_list();
  else if (c == 'd')
    convert_dictionary();
  else {
    unget_character(c);
    convert_string();
  }
}

int main(void) {
  /* Only convert a single value. This can be any data type including
     dictionary. */
  convert_value();
  return 0;
}
