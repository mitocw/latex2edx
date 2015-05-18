/*
 * This library is licensed under the MIT license.
 *
 * The MIT Licence (MIT)

 * Copyright (c) 2014-2015 Jolyon Bloomfield and Eric Heubel

 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

 * The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

function hideshow(object) {
  // Check to ensure that an attempt has been made
  submissions = $(object).parents('.problem').find('.submission_feedback');
  showanswerbutton = $(object).parents('.problem').find('.show');
  if ($(submissions) && !$(showanswerbutton)) {
      submissiontext = $(submissions).text().trim();
      poscut = parseInt(submissiontext.indexOf("of"));
      if (submissiontext.substring(14, poscut) == '0') {
          alert('You must make an attempt before viewing the solution.');
          return false;
      }
  }

  // If checks succeed proceed with show/hide
  hideshownocheck(object);
}

function hideshownocheck(object) {
  // Do the show/hide business
  stuff = $(object).parents('.hideshowbox').find('.hideshowcontent');
  text = $(object).parents('.hideshowbox').find('.hideshowbottom');
  arrow = $(object).parents('.hideshowbox').find('.toggleimage');
  arrowclass = $(arrow).attr('class');
  if ($(stuff).css('display') != 'none') {
      $(stuff).slideUp('slow');
      $(text).html('<a href="javascript: {return false;}">Show</a>');
      newclass = arrowclass.replace('up', 'down');
      $(arrow).attr('class', newclass);
  } else {
      $(stuff).slideDown('slow');
      $(text).html('<a href="javascript: {return false;}">Hide</a>');
      newclass = arrowclass.replace('down', 'up');
      $(arrow).attr('class', newclass);
  }
}
