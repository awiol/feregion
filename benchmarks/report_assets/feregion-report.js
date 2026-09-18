'use strict';
$(document).ready(function() {
    function escapeHtml(value) {
        return $('<div/>').text(value === null || value === undefined ? '' : String(value)).html();
    }

    function showFeregionPage() {
        $('#feregion-display').show();
        var body = $('#feregion-body');
        body.html('<p class="feregion-loading">Loading feregion benchmark summary…</p>');
        $.ajax({
            url: 'feregion.json' + '?timestamp=' + $.asv.main_timestamp,
            dataType: 'json',
            cache: true
        }).done(function(data) {
            var env = [];
            $.each(data.environment_parameters || {}, function(key, values) {
                if (values.length > 1 || key === 'machine') {
                    env.push('<li><strong>' + escapeHtml(key) + ':</strong> ' +
                             escapeHtml(values.join(', ')) + '</li>');
                }
            });

            var revisions = (data.revisions || []).slice().reverse().slice(0, 12).map(function(item) {
                var label = item.tags && item.tags.length ? item.tags.join(', ') : item.commit.slice(0, 8);
                return '<tr><td>' + escapeHtml(label) + '</td><td><code>' +
                       escapeHtml(item.commit.slice(0, 12)) + '</code></td></tr>';
            }).join('');

            var benchmarks = (data.benchmarks || []).map(function(item) {
                var view = '<a href="' + escapeHtml(item.scaling_href) + '">' +
                           (item.parameterized ? 'scaling view' : 'history view') + '</a>';
                return '<tr><td><strong>' + escapeHtml(item.pretty_name) + '</strong><br/><small>' +
                       escapeHtml(item.pretty_source || '') + '</small></td><td>' +
                       escapeHtml(item.param_names.join(', ') || 'none') + '</td><td>' + view + '</td></tr>';
            }).join('');

            body.html(
                '<div class="feregion-summary">' +
                '<h1>feregion benchmark summary</h1>' +
                '<p>This page is an additive project view over ASV\'s retained measurements. ' +
                'Use the native grid/list/graph pages for detailed exploration and the native ' +
                'Regressions page for ASV\'s sensitive step detector.</p>' +
                '<div class="row">' +
                '<div class="col-sm-4"><div class="well"><strong>' + data.benchmark_count +
                '</strong><br/>benchmark cases</div></div>' +
                '<div class="col-sm-4"><div class="well"><strong>' + data.revision_count +
                '</strong><br/>indexed revisions</div></div>' +
                '<div class="col-sm-4"><div class="well"><strong>' + data.regression_count +
                '</strong><br/>ASV regression signals</div></div>' +
                '</div>' +
                '<div class="alert alert-info"><strong>Regression interpretation.</strong> ' +
                escapeHtml(data.asv_regression_note) + '</div>' +
                '<div class="alert alert-warning"><strong>Migration authority.</strong> ' +
                escapeHtml(data.migration_authority_note) + '</div>' +
                '<div class="alert alert-info"><strong>Throughput.</strong> ' +
                escapeHtml(data.throughput_note) + '</div>' +
                '<h2>Environment coverage</h2><ul>' + env.join('') + '</ul>' +
                '<h2>Recent measured revisions</h2>' +
                '<table class="table table-condensed table-striped"><thead><tr><th>tag / identity</th>' +
                '<th>commit</th></tr></thead><tbody>' + revisions + '</tbody></table>' +
                '<h2>Benchmark cases</h2><p>Parameterized cases link directly to a load-size x-axis ' +
                'with logarithmic timing scale so scaling is visible without manual setup.</p>' +
                '<table class="table table-condensed table-striped"><thead><tr><th>case</th><th>parameters</th>' +
                '<th>curated view</th></tr></thead><tbody>' + benchmarks + '</tbody></table>' +
                '<h2>Native ASV views</h2><p><a href="#/regressions">Regressions</a> · ' +
                '<a href="#/summarylist">Benchmark list</a> · <a href="#/">Benchmark grid</a></p>' +
                '</div>'
            );
        }).fail(function() {
            body.html('<div class="alert alert-danger">Unable to load feregion.json.</div>');
        });
    }

    $.asv.register_page('feregion', showFeregionPage);
    $(window).on('hashchange.feregion', function() {
        var info = $.asv.parse_hash_string(window.location.hash);
        if (info.location.join('/') !== 'feregion') {
            $('#feregion-display').hide();
        }
    });
});
