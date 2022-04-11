#!/usr/bin/perl -wT
#
# skoltSaami.cgi
#
# CGI-bin script.  
# Converts a lexeme + theme vowel into a KATR output.
# Raphael Finkel 3/2016

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
	my $language = 'skoltSaami'; # use lower case
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

my %diphthongs = (
	iõ => 1,
	iâ => 1,
	ie => 1,
	eâ => 1,
	eä => 1,
	uõ => 1,
	uå => 1,
	ue => 1,
	uä => 1,
	lj => 1,
	"’j" => 1, 
);

sub splitWord { # introduce spaces between letters
	my ($word) = @_;
	$word =~ s/\s*$//; # trim both ends
	$word =~ s/^\s*//;
	# print STDERR "word is $word\n";
	my @parts = split(/(?=\X)/, $word);
	my @answer;
	my $prev = '';
	# try joining
	while (@parts) {
		my $part = shift @parts;
		if ($part eq $prev or exists($diphthongs{"$prev$part"})) {
			$answer[-1] .= $part;
			$prev = '';
		} else {
			push @answer, $part;
			$prev = $part;
		}
	} # each part
	# print STDERR "parts are " , join(' ', @answer) . "\n";
	return join(' ', @answer);
} # splitWord

sub dictPartsToKATR {
	my (@parts) = @_;
	my @answer;
	my $node;
	my @path = ();
	my $type = shift @parts; # verb or noun
	# sayError("type is $type");
	if ($type eq 'verb') {
		my $definition;
		for my $part (@parts) {
			# print STDERR "working on $part\n";
			if ($part =~ s/^(basic|weak|strong):\s+//) { # stem
				my $stemKind = $1;
				my $stem = splitWord($part);
				push @answer, "\t{$stemKind} = $stem";	
				$node = 'TheVerb'; # most likely overridden by English meaning
			} elsif ($part =~ s/^en:\s+//) { # convert English to KATR node name
				$part =~ s/\s+$//; # trim
				$part =~ s/ (\w)/uc $1/eg;
				$part =~ s/[(),;]/_/g;
				$definition = ucfirst $part . ":";
			} elsif ($part =~ s/^su:\s+//) { # Finnish definition
				# use it if no English available
				next if defined($definition);
				$part =~ s/\s+$//; # trim
				$part =~ s/ (\w)/uc $1/eg;
				$part =~ s/[(),;]/_/g;
				$definition = ucfirst $part . ":";
			} elsif ($part =~ s/^class:\s+(\d)//) {
				push @path, "class$1";
			} elsif ($part =~ s/^group:\s+(\w)//) {
				push @path, "group$1";
			} elsif ($part =~ s/^disyllabic: yes//) {
				push @path, 'disyllabic';
			} else {
				print STDERR "Unparseable part: [$part]\n";
			}
		} # each part
		unshift @answer, $definition;
		push @answer, "\t<> = VERB:<" . join(' ', @path) . '>';
		push @answer, "\t.";
		# print STDERR "converted [$origLine] to:\n" . join("\n", @answer) . "\n";
	} else { # noun
		for my $part (@parts) {
			# print STDERR "working on $part\n";
			if ($part =~ s/^(basic|weak|strong):\s+//) { # stem
				my $stemKind = $1;
				my $stem = splitWord($part);
				push @answer, "\t{$stemKind} = $stem";	
				$node = 'TheNoun'; # most likely overridden by English meaning
			} elsif ($part =~ s/^en:\s+//) { # convert English to KATR node name
				$part =~ s/\s+$//; # trim
				$part =~ s/ (\w)/uc $1/eg;
				$part =~ s/[(),;]/_/g;
				unshift @answer, ucfirst $part . ":";
			} elsif ($part =~ s/^class:\s+(\d)//) {
				push @path, "class$1";
			} elsif ($part =~ s/^group:\s+(\w)//) {
				push @path, "group$1";
			} elsif ($part =~ s/^subClass:\s+(\w+)//) {
				push @path, "$1";
			} else {
				print STDERR "Unparseable part: [$part]\n";
			}
		} # each part
		push @answer, "\t<> = NOUN:<" . join(' ', @path) . '>';
		push @answer, "\t.";
	} # noun
	# sayError(join("<br>", @answer));
	return(join("\n", @answer));
} # dictPartsToKATR

sub runKATR {
	my (@dictParts) = @_;
	# print STDERR "dictParts is $dictParts\n";
	# print STDERR dictLineToKATR($dictParts);
	my $tmpFile = "/tmp/${language}KATR" . $$;
	system("cp $LanguageKATR $tmpFile.katr");
	open KATR, ">>$tmpFile.katr" or die("Cannot write to $tmpFile.katr");
	binmode KATR, ":utf8";
	print KATR "\n" . dictPartsToKATR(@dictParts);
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
	open VOCAB, $vocabFile or die("Can't read $vocabFile\n");
	binmode VOCAB, ":utf8";
	while (my $line = <VOCAB>) {
		if ($line =~ /$query/) {
			showVocab($line, $query);
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

sub showVocab {
	my ($line, $query) = @_;
	my @toPrint;
	my @parts = split(/(?=\s*\b\w+:)/, $line);
	# if ($line =~ /verb: (\X+) en: (.*)/) {
	# print STDERR "parts: " . join("|", @parts) . "\n"; exit(0);
	if ($parts[0] =~ /verb: (\X+)/) {
		my ($headword) = $1;	
		my ($english, $finnish) = ('', '');
		shift @parts;
		for my $part (@parts) {
			if ($part =~ /en: (.*)/) {
				$english = $1;
			} elsif ($part =~ /su: (.*)/) {
				$finnish = $1;
			}
		} # each part
		# my $visible = uri_escape_utf8($headword);
		my $inf = $headword;
		my $vis_english = $english eq '' ? $finnish : $english;
		$vis_english =~ s/\s+(\w)/uc $1/eg;
		$headword =~ s/$query/<span class='result'>$query<\/span>/;
		$english =~ s/$query/<span class='result'>$query<\/span>/;
		$finnish =~ s/$query/<span class='result'>$query<\/span>/;
		# $visible =~ s/([^[:ascii:]])/sprintf("%%%x", ord($1))/eg;
		push @queryResults, {entry =>
			"$headword " .
			($english eq '' ? '' : "(English: $english) ") .
			($finnish eq '' ? '' : "(Finnish: $finnish) ") .
			"<span
				class='myLink'
				onclick='post(\"$progName\", {infinitive:\"$inf\", en:\"$vis_english\"})' 
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
		# my $url = "$progName?noun=$visible;en=$vis_english" .
		# 	(@moreInfo ? '&' . join('&', @moreInfo) : '');
		push @queryResults, {entry =>
			"$headword ($english) 
			<span
				class='myLink'
				onclick='post(\"$progName\", {" . join(', ', @moreInfo) . "})'
			>click to see forms</span>"};
	} # noun
} # showVocab

sub analyzeInfinitive {
	my ($infinitive) = @_;
	my ($basic, $theme, $group, $class, $strong, $weak, @parts);
	push @parts, 'verb';
	# print STDERR "got infinitive $infinitive\n";
	$infinitive =~ /(.*)(â|a|e)d$/ or
		sayError("$infinitive is not a proper infinitive form.");
	($basic, $theme) = ($1, $2);
	param('basic', $basic);
	$class =
		($basic =~ /j$/) ? '3' :
		($basic =~ /e$/) ? '4' :
		($basic =~ /(\X)\1$/) ? '1' :
		'2';
	param('class', $class);
	$group = $theme eq 'â' ? 'A' : $theme eq 'a' ? 'B' : 'C';
	if ($class =~ /[24]/) { # always look like group C; check vowel height
		# print STDERR "computing group; originally $class / $group\n";
		if ($basic =~ /ʹ/) {
			$group = 'C';
		} elsif ($basic =~ /$low/) {
			$group = 'B';
		} else {
			$group = 'A';
		}
		# print STDERR "computed group; now $class / $group\n";
	} # compute group for classes 2 and 4
	param('group', $group);
	if ($basic =~ /$vowel.*$consonant.*$vowel/) {
		push @parts, "disyllabic: yes";
	}
	if ($group eq 'B') { # stem is low
		$basic =~ s/o/O/g;
	}
	if ($class eq '1') { # must provide weak and strong stems
		$basic =~ /(($vowel)+)(ʹ)?(($consonant)+)$/ or
			sayError("Can't parse class 1 stem [$basic]");
		my ($stemVowels, $stemConsonants) = ($1, $4);
		$weak = $strong = $basic; # first guess
		if ($stemConsonants =~ /($consonant)(\X)\2$/) {
			# consonant cluster like štt
			$weak =~ s/\X$//; # only undouble last consonant
			if ($stemVowels =~ /^\X$/) { # only 1 stem vowel
				$weak =~ s/($stemVowels)/$1$1/; # as in njOOrǥ
			}
		} elsif ($stemConsonants =~ /kk$/) { # special case
			$weak =~ s/kk$/ǥǥ/;
			if ($stemVowels =~ /^\X$/) { # only 1 stem vowel
				$weak =~ s/($stemVowels)/$1$1/; # as in njOOrǥ
			}
		} elsif ($stemConsonants =~ /(\X)\1$/) {
			$weak =~ s/\X$//; # undouble last consonant
			$weak =~ s/t$/d/; # as in teâvõõtt
			$weak =~ s/ǧ$/lj/; # as in vuä'lǧǧ
			if ($stemVowels =~ /^\X$/) { # only 1 stem vowel
				$weak =~ s/($stemVowels)/$1$1/; # as in njOOrǥ
			}
		} # doubled final consonant in basic stem
		param('weak', $weak);
		if ($stemVowels =~ /^(\X)\1$/) {
			my $repeated = $1;
			$strong =~ s/$stemVowels/$repeated/;
		}
		param('strong', $strong);
	} # computed weak and strong stems
	return ($basic, $theme, $group, $class, $strong, $weak, $class, @parts);
} # analyzeInfinitive

sub doManualVerb { # handle a web request for a manual form
	my @parts = ('verb');
	# my $infinitive = Untaint(decode("utf-8", param('infinitive')));
	my $infinitive = Untaint(scalar param('infinitive'));
	my ($basic, $theme, $group, $class, $strong, $weak);
	if (defined $infinitive) {
		($basic, $theme, $group, $class, $strong, $weak, $class, @parts) =
			analyzeInfinitive($infinitive);
	} # we have the infinitive; derive the rest from that
	# print STDERR "Class $class group $group\n";
	$class = Untaint(scalar param('class'));
		mustHave($class, "class");
		push @parts, "class: $class";
	$group = Untaint(scalar param('group'));
		mustHave($group, "group");
		push @parts, "group: $group";
	$basic = Untaint(scalar param('basic'));
		mustHave($basic, "basic stem");
		push @parts, "basic: $basic";
	if ($class eq '1') {
		$strong = Untaint(scalar param('strong'));
			mustHave($strong, "strong");
			push @parts, "strong: $strong";
		$weak = Untaint(scalar param('weak'));
			mustHave($weak, "weak");
			push @parts, "weak: $weak";
	}
	my $english = Untaint(scalar param('en'));
		mustHave($english, "English meaning");
		push @parts, "en: $english";
	# print STDERR "entry is \n$entry\n";
	# sayError("parts: " . join('<br>', @parts));
	runKATR(@parts);
} # doManualVerb

sub doManualNoun { # handle a web request for a manual form
	my @parts = ('noun');
	my $headword = Untaint(scalar param('noun'));
	my ($basic, $weak, $strong, $group, $subClass, $class);
	$class = Untaint(scalar param('class'));
		mustHave($class, "class");
		push @parts, "class: $class";
	$subClass = Untaint(scalar param('subClass'));
		push @parts, "subClass: $subClass" if defined($subClass); 
	$basic = Untaint(scalar param('basic'));
		# sayError("basic is $basic");
		$basic = $headword unless defined($basic);
		push @parts, "basic: $basic";
	$group = Untaint(scalar param('group'));
		if (!defined($group) && $class eq '1') { # compute group for class 1
			if ($basic =~ /ʹ/) {
				$group = 'C';
			} elsif ($basic =~ /iõ|iâ|uõ|uå|u|o|a|i|e|õ/) {
				$group = 'A';
			} else {
				$group = 'B';
			}
		} # compute group
		mustHave($group, "group");
		push @parts, "group: $group";
	$weak = Untaint(scalar param('weak'));
		mustHave($weak, "weak");
		push @parts, "weak: $weak";
	$strong = Untaint(scalar param('strong'));
		mustHave($weak, "strong");
		push @parts, "strong: $strong";
	my $english = Untaint(scalar param('en'));
		mustHave($english, "English meaning");
		push @parts, "en: $english";
	my $entry = join(' ', @parts);
	# print STDERR "entry is \n$entry\n";
	runKATR(@parts);
} # doManualNoun

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
	} elsif (defined(param('infinitive'))) {
		print "Content-Type: text/html; charset=utf-8\n\n";
		doManualVerb();
	} elsif (defined(param('noun'))) {
		print "Content-Type: text/html; charset=utf-8\n\n";
		doManualNoun();
	} else {
		printManual();
	}
	# $dictLine = 'verb: foo en: testing'; # debug
	# $dictLine =~ s/%(\w\w)/sprintf("%c", hex($1))/eg;
} # tryIt

sub Untaint {
	my ($what) = @_;
	return undef if (!defined($what));
	$what =~ s/[&*`\$|\s;]//g; # remove suspicious characters
	$what =~ /(.*)/; # untaint
	return($1);
} # Untaint

init();
doIt();
