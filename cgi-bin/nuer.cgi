#!/usr/bin/perl -wT
#
# nuer.cgi
#
# CGI-bin script.  
# Converts a verb stem and extra information into KATR output.
# Raphael Finkel 5/2016

# use CGI::Simple::Standard qw(:standard -debug2);
use CGI::Simple::Standard qw(:standard -debug);
use CGI::Carp qw(fatalsToBrowser);
use Encode;
use URI::Escape;
use HTML::Template;
# use Encode;
use strict;
use utf8;

# constants
	my $language = 'nuer'; # use lower case
	my $wordDir = "/homes/raphael/links/r";
	my $KATRScript = './katr.cgi';
	my $formFile = "$language.cgi";
	my $within = '/homes/raphael/bin/within';
	my $LanguageKATR = "/homes/raphael/links/r/$language.katr";
	my $maxDepth = 100; # no indentation is this deep
	my $HTMLtemplateFile = "$language.tmpl"; # output template
	my $vocabFile = "/homes/raphael/links/r/$language.vocab";

# global variables
	my @contextLines;
	my (%pathToAbbrev, %abbrevToEnglish, %abbrevToPath);
	my $HTML = HTML::Template->new(utf8 => 1, filename => $HTMLtemplateFile);
	my @queryResults;
	my $progName;

sub init {
	$0 =~ /([^\/]+)$/;
	$progName = $1;
	binmode STDIN, ":utf8";
	binmode STDOUT, ":utf8";
	binmode STDERR, ":utf8";
	$ENV{'PATH'} = '/bin:/usr/bin:/usr/local/bin:/usr/local/gnu/bin';
	$| = 1; # flush output
} # init

sub splitWord { # introduce spaces between letters
	my ($word) = @_;
	$word =~ s/\s*$//; # trim both ends
	$word =~ s/^\s*//;
	# print STDERR "word is $word\n";
	my @parts;
	# split(/(?=\X)/, $word) seems not to work, so we split manually.
	while ($word =~ s/^(\X)//) {
		push @parts, $1;
	}
	# print STDERR "parts are " , join(', ', @parts) . "\n";
	return join(' ', @parts);
} # splitWord

sub dictPartsToKATR {
	my (@parts) = @_;
	my @answer;
	my @path = ();
	my $stem;
	if ($parts[0] =~ /verb/) {
		my $definition;
		for my $part (@parts) {
			# print STDERR "working on $part\n";
			if ($part =~ s/^en:\s+//) { # convert English to KATR node name
				$definition = $part;
			} elsif ($part =~ s/^verb:\s+//) {
				$stem = splitWord($part);
			} elsif ($part =~ s/^notes:\s+//) {
				push @path, $part;
			}
		} # each part
		$definition =~ s/\s+$//; # trim
		$definition =~ s/ (\w)/uc $1/eg;
		$definition =~ s/\s*\(.*//; # just the bare definition
		$definition =~ s/[,;\.]/_/g;
		$definition =~ s/[-]//g;
		$definition = ucfirst $definition . ":";
		unshift @answer, $definition;
		push @answer, "\t<> = VERB:<" . join(' ', @path) . '>';
		push @answer, "\t<stem> = $stem";
		push @answer, "\t.";
		# print STDERR "converted [$origLine] to:\n" . join("\n", @answer) . "\n";
	} # verb
	# sayError(join("<br>", @answer));
	return(join("\n", @answer));
} # dictPartsToKATR

sub runKATR {
	my (@dictParts) = @_;
	# print STDERR "dictParts is " . join(', ', @dictParts) . "\n";
	# print STDERR dictPartsToKATR(@dictParts);
	my $tmpFile = "/tmp/${language}KATR" . $$;
	system("cp $LanguageKATR $tmpFile.katr");
	open KATR, ">>$tmpFile.katr" or die("Cannot write to $tmpFile.katr");
	binmode KATR, ":utf8";
	print KATR "\n" . dictPartsToKATR(@dictParts) . "\n";
	close KATR;
	# print STDERR "look in $tmpFile.katr\n"; exit(0);
	delete $ENV{'REQUEST_METHOD'}; # conflicts with subordinate cgi-bin call
	my $command = "/bin/echo FileName=$tmpFile.katr | $within 10 $KATRScript 2>&1";
	# print "<pre>$command</pre><br>\n";
	system($command);
	# print "<!-- was result of [$command] -->\n";
	# print "echo FileName=$tmpFile.katr | $KATRScript\n";
	# print "<!-- dictParts is [$dictParts] -->\n";
	unlink "$tmpFile.katr";
} # runKATR

sub printManual {
	# generate a form so the user can try a new word
	print "Content-Type: text/html; charset=utf-8\n\n";
	print $HTML->output();
} # printManual

sub sayError {
	my ($msg) = @_;
	print "Content-Type: text/html; charset=utf-8\n
	<head><title>error</title></head><body>
	<span style='color:red;font-weight:bold'>$msg\n
		</span></html></body>\n";
	exit(0);
} # sayError

sub mustHave {
	my ($content, $name) = @_;
	if (!defined($content) || length($content) == 0) {
		sayError("You must supply the $name.");
	}
} # mustHave

my $vowel = 'a|å|ä|â|e|i|o|õ|u|O';
my $low = 'å|ä|â|O';
my $consonant =
	'p|b|t|d|đ|ǩ|g|ǧ|ǧ|k|ǥ|m|n|ŋ|r|f|v|đ|s|z|š|ž|j|h|ǥ|c|ʒ|č|ǯ|l|’j';

sub doQuery {
	my ($query) = @_;
	my $shortQuery = unexpandVowels($query);
	open VOCAB, $vocabFile or die("Can't read $vocabFile\n");
	binmode VOCAB, ":utf8";
	while (my $line = <VOCAB>) {
		if ($line =~ /$query/) {
			showVocab($line, $query);
		} elsif ($line =~ /$shortQuery/) {
			showVocab($line, $shortQuery);
		}
	} # each line of vocab
	close VOCAB;
	if (@queryResults == 0) {
		push @queryResults, {entry =>
			"Cannot find <span class='bold'>$query</span> in lexicon."};
	}
	$HTML->param(didQuery => 1);
	$HTML->param(results => \@queryResults);
	print "Content-Type: text/html; charset=utf-8\n\n";
	print $HTML->output();
} # doQuery

sub expandVowels {
	my ($word) = @_;
	$word =~ s/(\X)¹/$1/g;
	$word =~ s/(\X)²/$1$1/g;
	$word =~ s/(\X)³/$1$1$1/g;
	return $word;
} # expandVowels

sub unexpandVowels {
	my ($word) = @_;
	my $vowels = '(i|e|ɛ|a|ɔ|o|u)̤?';
	$word =~ s/¹//;
	$word =~ s/($vowels)\1\1/$1³/;
	$word =~ s/($vowels)\1/$1²/;
	$word =~ s/($vowels)(?![̤²³])/$1¹/;
	return $word;
} # unexpandVowels

sub showVocab {
	my ($line, $query) = @_;
	my @toPrint;
	my @parts = split(/(?=\s*\b\w+:)/, $line);
	# if ($line =~ /verb: (\X+) en: (.*)/) {
	# print STDERR "parts: " . join("|", @parts) . "\n"; exit(0);
	if ($parts[0] =~ /verb: (\X+)/) {
		my ($headword) = $1;	
		my $english  = '';
		my $nuer  = '';
		my $notes = '';
		shift @parts;
		for my $part (@parts) {
			if ($part =~ /en: (.*)/) {
				$english = $1;
			} elsif ($part =~ /notes: (.*)/) {
				$notes = $1;
			}
		} # each part
		# my $visible = uri_escape_utf8($headword);
		my $stem = $headword;
		$headword = expandVowels($headword);
		my $vis_english = $english eq '' ? $nuer : $english;
		$vis_english =~ s/\s+(\w)/uc $1/eg;
		$headword =~ s/$query/<span class='result'>$query<\/span>/;
		$english =~ s/$query/<span class='result'>$query<\/span>/;
		$nuer =~ s/$query/<span class='result'>$query<\/span>/;
		# $visible =~ s/([^[:ascii:]])/sprintf("%%%x", ord($1))/eg;
		push @queryResults, {entry =>
			"<span class='lexeme'>$headword</span> " .
			($english eq '' ? '' : "<span class='english'>$english</span> ") .
			($nuer eq '' ? '' : "<span class='nuer'>$nuer</span> ") .
			"<span
				class='myLink'
				onclick='post(\"$progName\", {
					verbStem:\"$stem\",
					en:\"$vis_english\",
					notes:\"$notes\"
				})' 
			>
			click to see forms</span>"};
	} elsif ($line =~ s/noun: (\X+) en: ([^:]+) //) {
		my ($headword, $english) = ($1, $2);
		my $visible = uri_escape_utf8($headword);
		my $noun = $headword;
		my $vis_english = $english;
		$vis_english =~ s/\s+(\w)/uc $1/eg;
		$headword =~ s/$query/<span class='result'>$query<\/span>/;
		$english =~ s/$query/<span class='result'>$query<\/span>/;
		my @moreInfo;
		# print "line is $line\n";
		my $params = [];
		for my $piece (split /(?= \w+:)/, $line) {
			$piece =~ s/ ?(.+): (.*)// or next;
			my ($attribute, $value) = ($1, $2);
			# push @moreInfo, "$attribute=" . uri_escape_utf8($value);
			push @moreInfo, "\"$attribute\": \"$value\"";
		}
		push @moreInfo, "\"noun\": \"$noun\"";
		push @moreInfo, "\"en\": \"$vis_english\"";
		# print "moreinfo: " . join('&', @moreInfo) . "\n";
		# my $url = "$progname?noun=$visible;en=$vis_english" .
		# 	(@moreInfo ? '&' . join('&', @moreInfo) : '');
		push @queryResults, {entry =>
			"$headword ($english) 
			<span
				class='myLink'
				onclick='post(\"$progName\", {" . join(', ', @moreInfo) . "})'
			>click to see forms</span>"};
	} # noun
} # showVocab

sub doManualVerb { # handle a web request for a manual form
	# my $infinitive = Untaint(decode("utf-8", param('infinitive')));
	my @parts;
	my $stem = Untaint(scalar param('verbStem'));
		mustHave($stem, "Verb stem");
		$stem = unexpandVowels($stem);
	push @parts, "verb: $stem";
	# print STDERR "Class $class group $group\n";
	my $english = Untaint(scalar param('en'));
		mustHave($english, "English meaning");
		push @parts, "en: $english";
	my @notes = param('notes');
	push @parts, "notes: " . Untaint(join(' ', @notes));
	my $ic = Untaint(scalar param('ic'));
		# print STDERR "ic is $ic\n";
		$parts[-1] .= " $ic";
	# sayError("parts: " . join('<br>', @parts));
	runKATR(@parts);
} # doManualVerb

sub doMutation { # handle a web request for a mutation
	my $stem = Untaint(scalar param('stem'));
		mustHave($stem, "stem");
		$stem = splitWord(unexpandVowels($stem));
	# print STDERR "mutating [$stem]\n";
	# shorthands
	my $vowels = 'i|e|ɛ|a|ɔ|o|u|i̤|e̤|ɛ̤|a̤|ɔ̤|o̤|ṳ';
	my $consonants = 'b|ç|d|d̪|f|g|h|k|l|m|n|p|r|r̥|s|t̪|v|z|y|ɣ|ŋ|j';
	my $tones = '¹|²|³';
	# sandhi
	$stem =~ s/($vowels)\s+³\s+($consonants)\s+N/$1 ² $2 M/g;
	$stem =~ s/($vowels)\s+²\s+($consonants)\s+N/$1 ¹ $2 M/g;
	$stem =~ s/($vowels)\s+³\s+($consonants)\s+O/$1 ² $2/g;
	$stem =~ s/($vowels)\s+²\s+($consonants)\s+O/$1 ¹ $2/g;
	$stem =~ s/O//g;
	$stem =~ s/M/N/g;
	$stem =~ s/b\s+N/f/g;
	$stem =~ s/d\s+N/r̥/g;
	$stem =~ s/ɣ\s+N/h/g;
	$stem =~ s/j\s+N/ç/g;
	$stem =~ s/N//g;
	$stem =~ s/M/N/g;
	$stem =~ s/i\s+($tones)\s+($consonants)\s+Q/iɛ $1 $2/g;
	$stem =~ s/i̤\s+($tones)\s+($consonants)\s+Q/i̤ɛ $1 $2/g;
	$stem =~ s/u\s+($tones)\s+($consonants)\s+Q/uɔ $1 $2/g;
	$stem =~ s/ṳ\s+($tones)\s+($consonants)\s+Q/ṳɔ $1 $2/g;
	$stem =~ s/ɔ\s+($tones)\s+($consonants)\s+Q/ɔa $1 $2/g;
	$stem =~ s/ɛ\s+($tones)\s+($consonants)\s+Q/ɛa $1 $2/g;
	$stem =~ s/o\s+($tones)\s+($consonants)\s+Q/oɔ $1 $2/g;
	$stem =~ s/o̤\s+($tones)\s+($consonants)\s+Q/o̤ɔ $1 $2/g;
	$stem =~ s/a̤\s+($tones)\s+($consonants)\s+Q/a $1 $2/g;
	$stem =~ s/Q//g;
	$stem =~ s/((?:$vowels| )*)\s+($tones)\s+($consonants)\s+H/$1́ $2 $3/g;
	$stem =~ s/((?:$vowels| )*)\s+($tones)\s+($consonants)\s+L/$1̀ $2 $3/g;
	$stem =~ s/((?:$vowels| )*)\s+($tones)\s+($consonants)\s+R/$1̌ $2 $3/g;
	$stem =~ s/((?:$vowels| )*)\s+($tones)\s+($consonants)\s+F/$1̂ $2 $3/g;
	$stem =~ s/($vowels)\s+($tones)\s+H/$1́ $2/g;
	$stem =~ s/($vowels)\s+($tones)\s+L/$1̀ $2/g;
	$stem =~ s/($vowels)\s+($tones)\s+R/$1̌ $2/g;
	$stem =~ s/($vowels)\s+($tones)\s+F/$1̂ $2/g;
	$stem =~ s/h\s+k/k/g;
	$stem =~ s/($vowels)($vowels)(̀|́|̂|̌)\s+¹/$1 $3 $2/g;
	$stem =~ s/($vowels)($vowels)(̀|́|̂|̌)\s+²/$1 $3 $2 $2/g;
	$stem =~ s/($vowels)($vowels)(̀|́|̂|̌)\s+³/$1 $3 $2 $2/g;
	$stem =~ s/($vowels)(̀|́|̂|̌)\s+¹/$1 $2/g;
	$stem =~ s/($vowels)(̀|́|̂|̌)\s+²/$1 $2 $1/g;
	$stem =~ s/($vowels)(̀|́|̂|̌)\s+³/$1 $2 $1 $1/g;
	# final fixup
	$stem =~ s/\s//g;
	$stem = expandVowels($stem);
	$HTML->param(mutation => $stem);
	print "Content-Type: text/html; charset=utf-8\n\n";
	print $HTML->output();
} # doMutation

sub escapedToUTF8 {
	my ($escaped) = @_;
	$escaped =~ s/%u([0-9A-F]{4})/sprintf("%c", hex($1))/eg;
	$escaped =~ s/%([0-9A-F]{2})/sprintf("%c", hex($1))/eg;
	return $escaped;
} # escapedToUTF8

sub doIt {
	my $dictLine;
	$HTML->param(didQuery => 0); # unless proven otherwise
	if (defined(param('query'))) {
		doQuery(Untaint(scalar param('query')));
	} elsif (defined(param('verbStem'))) {
		doManualVerb();
	} elsif (defined(param('stem'))) {
		doMutation();
	} else {
		printManual();
	}
	# $dictLine = 'verb: foo en: testing'; # debug
	# $dictLine =~ s/%(\w\w)/sprintf("%c", hex($1))/eg;
} # tryIt

sub Untaint {
	my ($what) = @_;
	return undef if (!defined($what));
	$what =~ s/[&*`\$|;]//g; # remove suspicious characters
	$what =~ /(.*)/; # untaint
	return($1);
} # Untaint

init();
doIt();
