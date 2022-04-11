#!/usr/bin/perl -wT
#
# irish.cgi
#
# CGI-bin script.  Depending on parameters, either looks up words in a list
# (param "search") or converts a dictionary entry (param "entry") into a KATR
# output.
# Raphael Finkel 7/2009

use CGI qw/:standard -debug/;
use CGI::Carp qw(fatalsToBrowser);
use Encode;
use strict;
use utf8;

# constants
	my $language = 'irish'; # use lower case
	my $wordDir = "/homes/raphael/cs/links/r";
	my $dictionaryFile = "$wordDir/$language.vocab";
	my $cgiDir = "http://www.cs.uky.edu/~raphael/linguistics"; # for CS
	my $KATRScript = '/homes/raphael/HTML/linguistics/katr.cgi';
	my $formFile = "$cgiDir/$language.cgi";
	my $within = '/homes/raphael/bin/within';
	my $LanguageKATR = "/homes/raphael/links/r/$language.katr";
	my $maxDepth = 100; # no indentation is this deep
	my $Debug = 0;

	my @shorthands = (
		# [shorthand in vocab, path, English expansion, applicable pos]
		['vadj', 'verbalAdjectiveSuffix', 'verbal adjective suffix', 'verb'],
		['vadjFull', 'verbalAdj', 'verbal adjective', 'verb'],
		['past', 'stem past', 'past stem', 'verb'],
		['pastEnding', 'endingPast', 'past ending', 'verb'],
		['pastDependent', 'stem past dependent', 'dependent past stem', 'verb'],
		['gerund', 'gerundSuffix', 'gerund suffix', 'verb'],
		['future', 'stem future', 'future stem', 'verb'],
		['contPres', 'stem contPres', 'continual present stem', 'verb'],
		['pl', 'nounSuffix pl', 'plural suffix', 'noun'],
		['genSg', 'nounSuffix genitive sg', 'genitive singular suffix', 'noun'],
		['nomSg', 'nounSuffix nominative sg', 'nominative singular suffix', 'noun'],
	);
	my %properties = (
		# property => English expansion
		1 => '1st conjugation',
		'1igh' => '1st conjugation, past tense in -igh',
		2 => '2nd conjugation',
		'2igh' => '2nd conjugation, past tense in -igh',
		m1 => '1st declension masculine',
		f2 => '2nd declension feminine',
		m3 => '3rd declension masculine',
		f3 => '3rd declension feminine',
		m4 => '4th declension masculine',
		f4 => '4th declension feminine',
		a1 => '1st class adjective',
		a2 => '2nd class adjective',
		a3 => '3rd class adjective',
		irreg => 'irregular',
	);

# globals
	my @contextLines;
	my (%pathToAbbrev, %abbrevToEnglish, %abbrevToPath);

sub init {
	binmode STDIN, ":utf8";
	binmode STDOUT, ":utf8";
	binmode STDERR, ":utf8";
	$ENV{'PATH'} = '/bin:/usr/bin:/usr/local/bin:/usr/local/gnu/bin';
	$| = 1; # flush output
	if ($Debug) {
		print header(-charset=>'UTF-8', -expires=>'-1d'),
			start_html(
				-encoding=>'UTF-8',
				-title=>'debugging output',
				-head=>Link({-rel=>'icon',
					-href=>'kentucky_wildcats.ico'}),
				),
			"\n";
	}
	for my $entryPtr (@shorthands) {
		my ($abbrev, $path, $english) = @$entryPtr;
		$pathToAbbrev{$path} = $abbrev;
		$abbrevToEnglish{$abbrev} = $english;
		$abbrevToPath{$abbrev} = $path;
	} # each $entryPtr in @shorthands
} # init

sub nounExtras { # discover noun extras, generate shorter noun stem
	my ($word) = @_;
	$word =~ s/\s*$//; # trim both ends
	$word =~ s/^\s*//;
	my @extras;
	push @extras, 'stemNach' if $word =~ s/nach$//;
	push @extras, 'stemAch' if $word =~ s/ach$//;
	push @extras, 'stemEann' if $word =~ s/eann$//;
	push @extras, 'stemR' if $word =~ s/é\(i\)r$/é(i)/;
	push @extras, 'stemR' if $word =~ s/éar$/é/;
	push @extras, 'stemU' if $word =~ s/ú$//;
	push @extras, 'stemAil' if $word =~ /á\(i\)l$/; # but keep the ending
	push @extras, 'stemAi' if $word =~ /aí$/; # but keep the ending
	push @extras, 'stemAis' if $word =~ /ais$/; # but keep the ending 
	return ($word, @extras);
} # nounExtras

sub adjectiveExtras { # discover adjective extras, generate shorter adjective stem
	my ($word) = @_;
	$word =~ s/\s*$//; # trim both ends
	$word =~ s/^\s*//;
	my @extras;
	push @extras, 'stemAch' if $word =~ s/ach$//;
	return ($word, @extras);
} # adjectiveExtras

sub splitWord { # introduce spaces between letters
	my ($word) = @_;
	$word =~ s/\s*$//; # trim both ends
	$word =~ s/^\s*//;
	my (@answer);
	# print STDERR "word is $word\n";
	$word =~ s/\(i\)/I_/g; # epenthetic i
	$word =~ s/\(a\)/A_/g; # epenthetic a
	$word =~ s/\(i-\)/I1/g; # epenthetic i, but not before t
	$word =~ s/\(i\+\)/I4/g; # epenthetic i, also before I2
	$word =~ s/\(\+\)/A+/g; # force epenthesis
	$word =~ s/\(i!\)/I+/g; # force epenthesis
	while ($word =~ s/((I|A)(\d|_|\+)|[cfptsgdbm]h|ng|\X)//i) {
		my $letter = $1;
		push @answer, 'O_' if $letter =~ /[BCDFGPST]/; # caps => no lenition
		push @answer, ($letter =~ /^(I|A)/ ? $letter : lc $letter);
	}
	# print STDERR "I now have " . join(' ', @answer) . "\n";
	return join(' ', @answer);
} # splitWord

sub dictLineToKATR {
	my ($dictLine) = @_;
	my $answer;
	my (@properties) = ();
	my @parts;
	# print STDERR "dictLine is $dictLine\n";
	my $origLine = $dictLine;
	while ($dictLine =~ s/(\w+:.+?)(?=\w+:)//) {
		my $piece = $1;
		push @parts, $piece;
	}
	push @parts, $dictLine;
	my $node;
	for my $part (@parts) {
		# print STDERR "working on $part\n";
		if ($part =~ s/^(verb|noun|adj):\s+//) { # stem
			my $pos = $1;
			my ($stem, @extras);
			if ($pos eq 'noun') {
				($part, @extras) = nounExtras($part);
			} elsif ($pos eq 'adj') {
				($part, @extras) = adjectiveExtras($part);
			}
			$stem = splitWord($part);
			$answer .= "\t{stem} = $stem\n";	
			$node = ucfirst $pos; # most likely overridden by later information
			push @properties, @extras;
		} elsif ($part =~ s/^en:\s+//) { # convert English to KATR node name
			$part =~ s/\s+$//; # trim
			$part =~ s/ (\w)/uc $1/eg;
			$part =~ s/[(),;]/_/g;
			$answer = ucfirst $part . ":\n" . $answer;
		} elsif ($part =~ s/^1:\s*//) {
			push @properties, 'conj1';
			$node = 'Verb';
		} elsif ($part =~ s/^(\d)igh:\s*//) {
			my $conj = $1;
			$node = "Conj${conj}igh";
		} elsif ($part =~ s/^2:\s*//) {
			push @properties, 'conj2';
			$node = 'Verb';
		} elsif ($part =~ s/^(m|f)(\d):\s*//) {
			my ($gender, $declension) = ($1, $2);
			$gender = uc $gender;
			$node = "Noun$gender$declension";
		} elsif ($part =~ s/^a(\d):\s*//) {
			my $form = $1;
			$node = "Adj$form";
		} elsif ($part =~ s/^note:\s+//) {
			$answer .= "\t% $part\n";
		} elsif ($part =~ s/^irreg:\s+(\w+)//) {
			my $verb = ucfirst $1;
			$node = "Irreg$verb";
			$answer = "$verb:\n";
		} elsif ($part =~ s/^(\w+):\s+//) {
			my $code = $1;
			my $path = $abbrevToPath{$code};
			if (defined($path)) {
				my $theSplit = splitWord($part);
				$answer .= "\t{$path} = $theSplit\n";
				# print STDERR "now have [$answer]";
			} else {
				print STDERR "Unknown code: $code\n";
			}
		} else {
			print STDERR "Unparseable part: [$part]\n";
		}
	} # each part
	$answer .= "\t{} = $node:<" . join(' ', @properties) . ">\n\t.\n";
	# print STDERR "converted [$origLine] to:\n$answer\n";
	return($answer);
} # dictLineToKATR

sub runKATR {
	my ($dictLine) = @_;
	my $tmpFile = "/tmp/${language}KATR" . $$;
	system("cp $LanguageKATR $tmpFile.katr");
	open KATR, ">>$tmpFile.katr" or die("Cannot write to $tmpFile.katr");
	binmode KATR, ":utf8";
	print KATR "\n" . dictLineToKATR($dictLine);
	close KATR;
	# print STDERR "look in $tmpFile.katr\n"; exit(0);
	delete $ENV{'REQUEST_METHOD'}; # conflicts with subordinate cgi-bin call
	my $command = "/bin/echo FileName=$tmpFile.katr | $within 10 $KATRScript 2>&1";
	system($command);
	# print "<!-- was result of [$command] -->\n";
	# print "echo FileName=$tmpFile.katr | $KATRScript\n";
	# print "<!-- dictLine is [$dictLine] -->\n";
	unlink "$tmpFile.katr";
} # runKATR

sub printExplain {
	print "
	<p> Notes:</p>
	<ol><li>(i) is an epenthetic 'i' that occurs in some forms.
	</li><li>(i-) like (i) but it does not become 'i' before 't'.
	</li><li>(i+) is like (i), but it occurs in more forms
	</li><li>(a) is an epenthetic 'a' that occurs in some forms
	</li><li>(+) and (i!) force a previous epenthetic vowel to appear in a situation
	where it usually would not.
	</li></ol>
	";
} # printExplain

my $serial = 0;
sub printForm {
	$serial += 1;
	print "
	<form action=\"$formFile\"
	method=\"post\" enctype=\"multipart/form-data\">
	A word or phrase or fragment to search (" . ucfirst($language) .
		" or English): 
	<input name=\"search\" type=\"text\" class=\"typein\"
		id=\"entry$serial\"
		onmouseover=\"getElementById('entry$serial').focus()\"/>
	<input type=\"submit\" value=\"search\"/>
	</form>
	\n";
} # printForm

sub printNicely {
	my ($line, $searchWord) = @_;
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
		if ($part =~ s/^(verb|noun|adj):\s+//) { # stem
			push @toPrint, "$part <span class=\"grammar\">$1</span>";
		} elsif ($part =~ s/^en:\s+//) { # convert English to KATR node name
			push @toPrint, "<span class=\"definition\">$part</span>";
		} elsif ($part =~ s/^note:\s+//) {
			push @toPrint, "<span class=\"source\">note: $part</span>";
		} elsif ($part =~ s/^(\w+):\s*//) {
			my $code = $1;
			$part =~ s/\s+$//;
			my $detail =
				defined($properties{$code}) ? $properties{$code} :
				defined($abbrevToEnglish{$code}) ? "$abbrevToEnglish{$code}" :
				$code;
			push @toPrint, "<span class=\"grammar\">$detail</span>" .
				(length($part) ? " $part" : '') . ';';
		} else {
			push @toPrint, $part;
		}
	} # each part
	my $toPrint = join(' ', @toPrint);
	$toPrint =~ s/\b(\Q$searchWord\E)\b/<span class=goodmatch>$1<\/span>/g;
	$toPrint =~ s/(?<!>)(\Q$searchWord\E)/<span class="weakmatch">$1<\/span>/g;
	$toPrint =~ s/(\Q$searchWord\E(?!<))/<span class="weakmatch">$1<\/span>/g;
	$origLine =~ s/"//g; # don't confuse the HTML
	print $toPrint .
		" <span onclick=\"submitIt('$origLine');\" class=\"myLink\">" .
		" click here for forms</span>\n";
} # printNicely

sub printManual {
	# generate a form so the user can try a new word
	print "" . br() . hr() . br();
	print "
	<form action=\"$formFile\"
	method=\"post\" enctype=\"multipart/form-data\">
	As an alternative,
	enter your own glossary information here to try out a word.
	<select name=\"pos\">
	<option value=\"verb\">Verb</option>
	<option value=\"noun\">Noun</option>
	<option value=\"adj\">Adjective</option>
	</select><br>
	Irish (cut and paste if you need: á é í ó ú>
		<input type=\"text\" name=\"irish\"><br>
	English equivalent <input type=\"text\" name=\"en\"> <br>
	\n";
	for my $shorthand (@shorthands) {
		print "<input type=\"checkbox\" name=\"" . "${$shorthand}[0]\">";
		print "${$shorthand}[2] (only for ${$shorthand}[3])\n";
		print "<input type=\"text\" name=\"val${$shorthand}[0]\"><br>\n";
	} # each shorthand
	for my $property (sort keys %properties) {
		print "<input type=\"checkbox\" name=\"$property\">";
		print "$properties{$property}<br>\n";
	} # each property
	print "<input type=\"submit\" value=\"Submit\">\n</form>\n";
} # printManual

sub mustHave {
	my ($content, $name) = @_;
	if (!defined($content) || length($content) == 0) {
		print header(-charset=>'UTF-8', -expires=>'-1d'),
			start_html(
				-encoding=>'UTF-8',
				-title=> (ucfirst $language) . " dictionary lookup",
				-style=>{'src'=>'http://www.cs.uky.edu/~raphael/dictstyle.css'},
			),
		"\n";
		print "You must supply the $name.\n</html></body>\n";
		exit(0);
	}
} # mustHave

sub doManual { # handle a web request for a manual form
	my @parts;
	my $pos = param('pos');
	my $irish = Untaint(scalar param('irish'));
	mustHave($irish, "Irish stem");
	push @parts, "$pos: $irish";
	my $english = Untaint(scalar param('en'));
	mustHave($english, "English meaning");
	push @parts, "en: $english";
	for my $shorthand (@shorthands) {
		next unless defined(param(${$shorthand}[0]));
		my $value = Untaint(scalar param("val${$shorthand}[0]"));
		push @parts, "${$shorthand}[0]: $value";
	} # each shorthand
	for my $property (sort keys %properties) {
		my $value = Untaint(scalar param($property));
		push @parts, "$property:" if defined($value) and $value eq 'on';
	} # each property
	my $entry = join(' ', @parts);
	mustHave(undef, "conjugation") if
		($pos eq 'verb' && $entry !~ /\b[12](igh)?:/);
	mustHave(undef, "declension") if
		($pos eq 'noun' && $entry !~ /\b[mf][1234]:/);
	mustHave(undef, "adjective class") if
		($pos eq 'adj' && $entry !~ /\ba[123]:/);
	runKATR(join(' ', @parts));
} # doManual

sub doSearch {
	print header(-charset=>'UTF-8', -expires=>'-1d'),
		start_html(
			-encoding=>'UTF-8',
			-title=> (ucfirst $language) . " dictionary lookup",
			-style=>{'src'=>'http://www.cs.uky.edu/~raphael/dictstyle.css'},
			),
		"\n";
	print "<script type=\"text/javascript\">
		function submitIt(params) {
			// params = encodeURI(params);
			// alert(params);
			document.getElementById('input').value = escape(params);
			document.getElementById('details').submit();
		}
		</script>\n";
	printForm();
	if (!defined(param('search')) || !length(param('search'))) {
		printManual();
	} else {
		print "" . br() . hr() . br();
		my $searchWord = decode_utf8(scalar param('search'));
		open WORDS, "<:utf8", $dictionaryFile or die("Can't read dictionary");
		my ($line, @printedLevels, $lastDepth, $lemmaDepth, $doPrint);
		$lastDepth = -1; # depth of previously output line
		$lemmaDepth = $maxDepth; # depth of current lemma that matches
		$doPrint = 0; # by default, don't print lines
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
				print "<form id=\"details\"
					action=\"$formFile\"
					method=\"post\">";
				print "<input id=\"input\" type=\"hidden\" name=\"entry\"
					value=\"verb: foo en: testing\">\n";
				$printedLevels[0] = 'nothing yet';
				for ($depth = 0; $depth <= $tabLength; $depth += 1) {
					if ($contextLines[$depth] ne $printedLevels[$depth]) {
						while ($lastDepth < $depth) {
							print "<ul>";
							$lastDepth += 1;
						}
						while ($lastDepth > $depth) {
							print "</ul>";
							$lastDepth -= 1;
						}
						print "<li>";
						printNicely($contextLines[$depth], $searchWord);
						print "</li>\n";
						$lastDepth = $depth;
						$printedLevels[$depth] = $contextLines[$depth];
					} # print context lines and the lemma
				} # for indendation depth
				print "</form>\n";
			} # if doPrint 
		} # one line
		while ($lastDepth >= 0) {
			print "</ul>";
			$lastDepth -= 1;
		}
		close WORDS;
		print "<p/>\n";
		print "" . br() . hr() . br();
		printExplain();
		printForm();
	} # word was given
	print end_html();
} # doSearch

sub escapedToUTF8 {
	my ($escaped) = @_;
	$escaped =~ s/%u([0-9A-F]{4})/sprintf("%c", hex($1))/eg;
	$escaped =~ s/%([0-9A-F]{2})/sprintf("%c", hex($1))/eg;
	return $escaped;
} # escapedToUTF8

sub doIt {
	my $dictLine;
	if (defined(param('entry'))) {
		$dictLine = escapedToUTF8(Untaint(scalar param('entry')));
		# print STDERR "dictLine is $dictLine\n";
		print header(-charset=>'UTF-8', -expires=>'-1d'),
			start_html(
				-encoding=>'UTF-8',
				-title=> (ucfirst $language) . " dictionary lookup",
				-style=>{'src'=>'http://www.cs.uky.edu/~raphael/dictstyle.css'},
				),
			"\n";
		runKATR($dictLine);
	} elsif (defined(param('search'))) {
		doSearch();
	} elsif (defined(param('pos'))) {
		doManual();
	} else {
		# $dictLine = 'verb: foo en: testing';
		# runKATR($dictLine);
		doSearch();
	}
	# $dictLine = 'verb: foo en: testing'; # debug
	# $dictLine =~ s/%(\w\w)/sprintf("%c", hex($1))/eg;
} # tryIt

sub Untaint {
	my ($what) = @_;
	return undef if (!defined($what));
	$what =~ s/[&*`\$|]//g; # remove suspicious characters
	$what =~ /(.*)/; # untaint
	return($1);
} # Untaint

init();
doIt();
