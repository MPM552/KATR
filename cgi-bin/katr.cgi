#!/usr/bin/perl -Tw
# The -T flag forces checking of tainted values, for security.

# CGI-bin script to accept KATR programs and print the theory

# We use gprolog, but as of version 1.4.5, it seems not to work.
# We can use swipl instead.

use CGI qw/:standard :debug/;
use CGI::Carp qw(fatalsToBrowser);
use Data::Dumper;
use Encode;
use strict;

require './showKATR.pm';

# constants
my $KATRdir = '/homes/raphael/links/r';
my $prefix = "/tmp/webKATR$$";

# variables
my $noFormat = 0; # whether to call the fancy formatter
my $compare = 0; # whether to compare against a given file
my $compareText; # text to compare against

sub init {
	$ENV{'PATH'} = '/bin:/usr/bin:/usr/local/bin'; # for security
	$| = 1; # flush output
	print header(-expires=>'+1m', -charset=>'UTF-8', -expires=>'-1d'),
		start_html(-title=>'Forms',
			-head=>Link({-rel=>'icon', -href=>'kentucky_wildcats.ico'}),
		);
	print "<h1>KATR output</h1>\n";
	binmode STDIN, ":utf8";
	binmode STDOUT, ":utf8";
	binmode STDERR, ":utf8";
	$noFormat = defined(param('noFormat'));
	$compare = defined(param('compare'));
	if ($compare) {
		# sayError("You must provide a file for comparison")
		# 	if param('compareFile') == '';
		my $InFile = param('compareFile');
		binmode $InFile, ":utf8";
		$/ = undef; # read file all at one gulp
		$compareText = <$InFile>;
		close $InFile;
	} # comparing
} # init

sub sayError {
	my ($msg) = @_;
	print $msg;
	cleanUp();
	exit(0);
} # sayError

sub readProg {
	my $Text;
	if (defined(param('FileName'))) {
		my $fileName = Untaint(scalar param('FileName'));
		sayError("Cannot read $fileName") unless -r $fileName;
		sayError ("$fileName is empty") if -z $fileName;
		$Text = decode("utf8", `cat $fileName`);
	} elsif (param('File')//'' ne "") {
		$/ = undef; # read file all at one gulp
		my $InFile = param('File');
		binmode $InFile, ":utf8";
		$Text = <$InFile>;
		# print "text is [$Text]\n";
	} else {
		$Text = decode("utf8", param('Text'));
		sayError("No text found") unless defined($Text);
	}
	$Text =~ s/\r//g; # remove \r
	my $KATRFile = "$prefix.katr";
	open PROG, ">$KATRFile" or die("Cannot write to $KATRFile");
	binmode PROG, ":utf8";
	print PROG $Text;
	close PROG;
} # readProg

my %assignedColor;
my $nextColorIndex = 0;

sub cleanUp {
	print "\n" . end_html() . "\n";
	unlink "$prefix.katr", "$prefix.katr.pro", "$prefix.sandhi.pl";
}

sub Untaint {
	my ($what) = @_;
	$what =~ s/[&*()`\$;\"]//g; # remove suspicious characters
	$what =~ /(.*)/; # untaint
	return($1);
} # Untaint

init();
readProg();
if ($compare) {
	execProgCompare($prefix, $compareText);
} elsif ($noFormat) {
	execProgNoFormat($prefix);
} else {
	execProg($prefix);
}
cleanUp();
