function hideshow(object) {
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

function hideshownocheck(object) {
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
