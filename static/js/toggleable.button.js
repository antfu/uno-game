/*
* @Author: Anthony
* @Date:   2016-04-02 11:13:28
* @Last Modified by:   Anthony
* @Last Modified time: 2016-04-03 00:09:32
*/

'use strict';

function init_toggleable_button(buttons)
{
  $('.toggleable.button').each(function(i,e){
    var element = $(e);
    element.addClass('ui compact inverted');
    element.data('active',function(value){
      if (value === undefined)
        return element.hasClass('active');
      if (value == true)
      {
        element.addClass('active').removeClass('basic');
        if (element.attr('data-active'))
          element.html(element.attr('data-active'));
      }
      else
      {
        element.removeClass('active').addClass('basic');
        if (element.attr('data-inactive'))
          element.html(element.attr('data-inactive'));
      }
      if (element.attr('data-cookies-key'))
        access_cookies(element.attr('data-cookies-key'),element.hasClass('active'));
    });
    element.data('click',function() {
      if (!element.attr('data-group'))
        element.data('toggle')();
      else
      {
        element.data('group')().each(function(i,e) {
          $(e).data('active')(false);
        });
        element.data('active')(true);
      }
    });
    element.data('toggle',function()
    {
      if (element.data('active')() == true)
        element.data('active')(false);
      else
        element.data('active')(true);
    });
    element.data('group',function() {
      if (element.attr('data-group'))
        return $('.toggleable.button[data-group="'+element.attr('data-group')+'"');
      else
        return undefined;
    });
    element.on('click',element.data('click'));

    /* Load from cookies */
    if (element.attr('data-cookies-key'))
      if (access_cookies(element.attr('data-cookies-key')))
        element.data('active')(true);
      else
        element.data('active')(false);
    else
      if (element.data('active')())
        element.data('active')(true);
      else
        element.data('active')(false);
  });
}

$(function(){
  init_toggleable_button();
});