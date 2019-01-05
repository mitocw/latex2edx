// modified from https://github.com/fdansv/marginotes
(function (factory) {
    if (typeof define === 'function' && define.amd) {
        define(['jquery'], factory);
    } else if (typeof module === 'object' && module.exports) {
        // Node/CommonJS
        module.exports = function( root, jQuery ) {
            if ( jQuery === undefined ) {
                // require('jQuery') returns a factory that requires window to
                // build a jQuery instance, we normalize how we use modules
                // that require this pattern but the window provided is a noop
                // if it's defined (how jquery works)
                if ( typeof window !== 'undefined' ) {
                    jQuery = require('jquery');
                }
                else {
                    jQuery = require('jquery')(root);
                }
            }
            factory(jQuery);
            return jQuery;
        };
    } else {
        // Browser globals
        factory(jQuery);
    }
}(function ($) {
    $.fn.marginotes = function (options) {
      options = options || {}
      var field = options.field || 'desc'
      var spans = this.filter('span')

      $('body').append('<div class="margintooltip" style="display: none;"></div>')
      spans.css({
        'border-bottom': '1px dashed #337ab7',
        'cursor': 'help'
      })
      this.hover(function (e) {
	var desc_span = $(this).find(".marginote_desc");

        var description = $(desc_span).html();
        var parent = $(this.parentElement)
        var position = parent.position()
	var offset = parent.offset();
        var tooltip = $('.margintooltip')

        var width = options.width || 150;
        var left = options.left || (offset.left - 30);
        var top = options.top || (offset.top);
        top = top + (options.top_offset || 0);

        console.log("[marginotes] width=", width,  " left=", left, " top=", top);
        console.log("[marginotes] position=", position, " offset=", offset, " desc_span=", desc_span);

        tooltip
          .css({
            'border-right': 'solid 2px #337ab7',
            'font-size': '13px',
            'left': left - width - 5,
            'min-height': parent.height(),
            'padding-right': '7px',
            'position': 'absolute',
            'text-align': 'right',
            'top': top,
            'width': width
          })
          // .text(description)
          .html(description)
          .stop()
          .fadeIn({
            duration:100,
            queue: false
          })
      }, function () {
        $('.margintooltip').stop()
        $('.margintooltip').fadeOut({
          duration: 100
        })
      })
    }
}));

try{
    $(".marginote").marginotes();
}
catch(err){
    console.log("Failed to instantiate margin notes, err=", err);
}
