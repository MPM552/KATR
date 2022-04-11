#!/usr/local/bin/perl -Tw
# The -T flag forces checking of tainted values, for security.

# CGI-bin script to look words up in my Shughni word list.
# This script displays words, and can call showShughni.cgi for KATR-generate
# details on any word.

use CGI qw/:standard -debug/;
use Encode;

# use_named_parameters(1);
use strict;
use utf8;

# parameters
	my $wordDir = "/homes/raphael/cs/links/r";
	my $dictionaryFile = "$wordDir/shughni.vocab";
	my $cgiDir = "http://www.cs.uky.edu/~raphael/linguistics";
	my $formFile = "$cgiDir/shughniDict.cgi";
	my $Debug = 0;

# constants
	my $maxDepth = 100; # no indentation is this deep

# globals
	my @contextLines;

sub init {
	$ENV{'PATH'} = '/bin:/usr/bin:/usr/local/bin:/usr/local/gnu/bin';
	$| = 1; # flush output
	if ($Debug) {
		print header(-expires=>'+1m', -charset=>'UTF-8');
	}
	binmode STDOUT, ":utf8";
} # init

my $serial = 0;
sub printForm {
	$serial += 1;
	print "
	<form action=\"$formFile\"
	method=\"post\" enctype=\"multipart/form-data\">
	A word or phrase or fragment to search (Shughni or English): 
	<input name=\"word\" type=\"text\" class=\"typein\"
		id=\"entry$serial\"
		onmouseover=\"getElementById('entry$serial').focus()\"/>
	</form>
	\n";
} # printForm

sub printNicely {
	my ($line, $searchWord) = @_;
	my %codeToKATR = (
		pres3sg => 'present 3 singular stem',
		presFem => 'present feminine stem',
		past => 'past stem',
		pastFem => 'past feminine stem',
		pastPl => 'past plural stem',
		perfect => 'perfect stem',
		perfectFem => 'perfect stem feminine',
		perfectPl => 'perfect stem plural',
		perfectMark => 'perfect marker',
		perfectFMark => 'perfect marker (feminine)',
		perfectMSgMark => 'perfect marker (masculine singular)',
		inf => 'infinitive stem',
	);
	my @toPrint;
	my @parts;
	chomp $line;
	my $origLine = $line;
	while ($line =~ s/(\w+:.+?)(?=\w+:)//) {
		my $piece = $1;
		# print "piece is [$piece]\n";
		push @parts, $piece;
	}
	push @parts, $line;
	for my $part (@parts) {
		if ($part =~ s/^verb:\s+//) { # stem
			push @toPrint, "<span class=\"grammar\">verb:</span> $part";
		} elsif ($part =~ s/^en:\s+//) { # convert English to KATR node name
			push @toPrint, "<span class=\"definition\">$part</span>";
		} elsif ($part =~ s/^trans:\s*//) {
			push @toPrint, "<span class=\"grammar\">transitive</span>";
		} elsif ($part =~ s/^intrans:\s*//) {
			push @toPrint, "<span class=\"grammar\">intransitive</span>";
		} elsif ($part =~ s/^short:\s*//) {
			push @toPrint, "<span class=\"grammar\">short</span>";
		} elsif ($part =~ s/^note:\s+//) {
			push @toPrint, "<span class=\"source\">note: $part</span>";
		} elsif ($part =~ s/^(\w+):\s+//) {
			my $code = $1;
			$part =~ s/\s+$//;
			$codeToKATR{$code} = $code unless defined($codeToKATR{$code});
			push @toPrint,
				"<span class=\"grammar\">$codeToKATR{$code}</span> $part;";
		} else {
			push @toPrint, $part;
		}
	} # each part
	my $toPrint = join(' ', @toPrint);
	$toPrint =~ s/\b(\Q$searchWord\E)\b/<span class="goodmatch">$1<\/span>/g;
	$toPrint =~ s/(?<!>)(\Q$searchWord\E)/<span class="weakmatch">$1<\/span>/g;
	$toPrint =~ s/(\Q$searchWord\E(?!<))/<span class="weakmatch">$1<\/span>/g;
	$origLine =~ s/["']//g; # don't confuse the HTML
	print $toPrint .
		" <span onclick=\"submitIt('$origLine');\" class=\"myLink\">" .
		" click here for forms</span>\n";
} # printNicely

sub doIt {
	my $searchWord = Untaint(decode_utf8(scalar param('word'))) // '';
	$searchWord //= '';
	print header(-charset=>'UTF-8', -expires=>'-1d'),
		start_html(
			-encoding=>'UTF-8',
			-title=>'Shughni dictionary lookup',
			-style=>{'src'=>'/~raphael/dictstyle.css'},
			),
		"\n";
	print "<script type=\"text/javascript\">
		function submitIt(params) {
			// params = encodeURI(params);
			document.getElementById('input').value = escape(params);
			// alert(escape(params));
			document.getElementById('details').submit();
		}
		</script>\n";
	printForm();
	print "" . br() . hr() . br();
	if ($searchWord =~ /^\s*$/) {
		print "Type in a word, either in Shughni or English, followed by the
		enter key.";
	} else {
		open WORDS, "<:utf8", $dictionaryFile or die("Can't read dictionary");
		my ($line, @printedLevels, $lastDepth, $lemmaDepth, $doPrint);
		$lastDepth = -1; # depth of previously output line
		$lemmaDepth = $maxDepth; # depth of current lemma that matches
		$doPrint = 0; # by default, don't print lines
		print "<form id=\"details\"
			action=\"showShughni.cgi\"
			method=\"post\">";
		print "<input id=\"input\" type=\"hidden\" name=\"dictLine\"
			value=\"verb: foo en: testing\"/>\n";
		while ($line = <WORDS>) { # one line
			$line =~ s/#.*//;
			next unless $line =~ /\w/;
			my $reduced = $line;
			$reduced =~ s/'//g;
			$line =~ /^(\t*)/;
			my $tabLength = length $1;
			if ($tabLength <= $lemmaDepth) { # forget about current lemma
				$lemmaDepth = $maxDepth;
			} 
			$contextLines[$tabLength] = $line;
			$doPrint = ($tabLength > $lemmaDepth); # print lines within lemma
			if (!$doPrint and $reduced =~ /\Q$searchWord\E/) { # new lemma
				$doPrint = 1;
				$lemmaDepth = $tabLength;
			}
			if ($doPrint) {	
				my $depth;
				for ($depth = 0; $depth <= $tabLength; $depth += 1) {
					if ($contextLines[$depth] ne ($printedLevels[$depth]//'')) {
						while ($lastDepth < $depth) {
							print "<ul><li>";
							$lastDepth += 1;
						}
						while ($lastDepth > $depth) {
							print "</li></ul>";
							$lastDepth -= 1;
						}
						# print "<li>";
						printNicely($contextLines[$depth], $searchWord);
						# print "</li>\n";
						$lastDepth = $depth;
						$printedLevels[$depth] = $contextLines[$depth];
					} # print context lines and the lemma
				} # for indendation depth
				while ($lastDepth >= 0) {
					print "</li></ul>";
					$lastDepth -= 1;
				}
			} # if doPrint 
		} # one line
		print "</form>\n";
		close WORDS;
		print "" . br() . hr() . br();
		printForm();
	} # word was given
	print end_html();
} # doIt

sub Untaint {
	my ($what) = @_;
	return undef unless defined $what;
	$what =~ s/[&*()`\$;|]//g; # remove suspicious characters
	$what =~ /(.*)/; # untaint
	return($1);
} # Untaint

init();
doIt();

# vim:nospell:
