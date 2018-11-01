/**
 * This ensures that only one import destination can be selected in the admin
 * UI. This is also enforced in the Model/DB layer as well. This is just to
 * prevent unneeded error messages.
 */
(function ($) {

  var checkboxSelector = '.form-row.has_original '
      + '.field-is_import_destination input[type=checkbox]'

  $().ready(function(){
    var checkboxes = $(checkboxSelector)

    checkboxes.click(function(event){
      // Uncheck all other checkboxes.
      checkboxes.not($(this)).attr('checked', false)
    })
  })

}(django.jQuery));
