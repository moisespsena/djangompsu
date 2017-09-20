(function ($) {
    $(document).ready(function () {
        var addAnchor = function (i, elem, parentSel) {
            if ($(elem).find("div.errors").length == 0) {
                $(elem).addClass("collapsed_").find("." + parentSel + "-title").first().append(' (<a id="' + parentSel +
                    '-collapser-' + i + '" class="collapse-toggle" href="#">' + gettext("Show") +
                    '</a>)');
            }
        };
        // Add anchor tag for Show/Hide link
        $("fieldset.collapse").each(function (i, elem) {
            addAnchor(i, elem, 'fieldset')
        });
        $(".inline-group.collapse").each(function (i, elem) {
            addAnchor(i, elem, 'inline-group')
        });

        var addToogleAnchor = function (parentSel) {
            var $parent = $(this).closest(parentSel+'.collapse');

            if ($parent.hasClass("collapsed_")) {
                // Show
                $(this).text(gettext("Hide"));
                $parent.removeClass("collapsed_")
                //.trigger("show.fieldset", [$(this).attr("id")]);
            } else {
                // Hide
                $(this).text(gettext("Show"));
                $parent.addClass("collapsed_")
                //.trigger("hide.fieldset", [$(this).attr("id")]);
            }
            return false;
        };

        // Add toggle to anchor tag
        $("fieldset.collapse a.collapse-toggle").click(function (ev) {
            return addToogleAnchor.call(this, 'fieldset');
        });
        // Add toggle to anchor tag
        $(".inline-group.collapse").each(function() {
            $(this).find('a.collapse-toggle:first').click(function (ev) {
                return addToogleAnchor.call(this, '.inline-group');
            })
        });

        $('fieldset').children('.fieldset-title').each(function(){
            $(this).closest('fieldset').addClass('fieldset-titled');
        });
    });
})(django.jQuery);
