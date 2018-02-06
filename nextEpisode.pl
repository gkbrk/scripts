#!/usr/bin/env perl
use strict;
use warnings;

use HTTP::Tiny;

sub http_get {
    my $http = HTTP::Tiny->new;
    return $http->get($_[0])->{content};
}

my @series;
my $html = http_get "https://next-episode.net/recent";
while ($html =~ /font-weight:inherit"><a href="\/.*?">(.*?)<\/a><\/h3>&nbsp;-&nbsp;(\d+)x(\d+) - <span style="color:#888888">(.*?)<\/span>/g) {
    push(@series, $1." Season ".$2." Episode ".$3." ".$4);
}

my @favorites = ("arrow", "flash", "legends of tomorrow", "grimm", "limitless",
                    "izombie", "magicians", "person of interest", "daredevil",
                    "mr. robot");

foreach my $episode (@series) {
    foreach my $fav (@favorites) {
        if ($episode =~ /$fav/i) {
            print $episode, "\n";
        }
    }
}
