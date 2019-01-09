#!/bin/bash

EXPECTED_ARGS=1
E_BADARGS=65
MAX_PYLINT_VIOLATIONS=2500
MAX_PEP8_VIOLATIONS=1220
PACKAGE_NAME=latex2edx

progname=$(basename $0) 
usage()
{

	cat <<EOF
Usage: test.sh [options]

Run the test runner and optional quality checks

Options:
 --help print this help message
 -q or --with-quality run pylint and pep8 on code
 -d or --diff-cover report of coverage in diff from origin/master
 -c or --with-coveralls run coveralls at the end (prompting for repo token)

EOF
}

SHORTOPTS="qcd"
LONGOPTS="help,with-quality,with-coveralls,diff-cover"

if $(getopt -T >/dev/null 2>&1) ; [ $? = 4 ] ; then # New longopts getopt.
 OPTS=$(getopt -o $SHORTOPTS --long $LONGOPTS -n "$progname" -- "$@")
else # Old classic getopt.
 # Special handling for --help on old getopt.
 case $1 in --help) usage ; exit 0 ;; esac
 OPTS=$(getopt $SHORTOPTS "$@")
fi

if [ $? -ne 0 ]; then
 echo "'$progname --help' for more information" 1>&2
 exit 1
fi

eval set -- "$OPTS"
quality=false
coveralls=false
diffcover=false
while [ $# -gt 0 ]; do
	: debug: $1
	case $1 in
		--help)
			usage
			exit 0
			;;
		-q|--with-quality)
			quality=true
			shift
			;;
		-c|--with-coveralls)
			coveralls=true
			shift
			;;
		-d|--diff-cover)
			diffcover=true
			shift
			;;
		--)
			shift
			break
			;;
		*)
			echo "Internal Error: option processing error: $1" 1>&2
			exit 1
			;;
	esac
done


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Using git version $(git --version)"

nosetests --with-coverage --cover-html --cover-package=$PACKAGE_NAME,$PACKAGE_NAME.test --exclude testtex
test_results=$?

if $quality; then
	# Show nice reports
	pylint --rcfile=$DIR/.pylintrc $PACKAGE_NAME
	pep8 $PACKAGE_NAME --max-line-length=120
	# Run again for automated violation testing
	pylint_violations=$(pylint --rcfile=$DIR/.pylintrc $PACKAGE_NAME -r n | grep -v '\*\*\*\*\*\*\*\*\*\*' | wc -l)
	pep8_violations=$(pep8 $PACKAGE_NAME | wc -l)
fi

if $diffcover; then
	coverage xml -i
	diff-cover coverage.xml
	rm coverage.xml
fi

if $coveralls; then
	echo "What is the coverall repo token?"
	read token
	echo "repo_token: $token" > $DIR/.coveralls.yml
	coveralls
	rm $DIR/.coveralls.yml
fi

exit_code=0

if [[ $test_results -ne 0 ]]; then
	echo "Unit tests failed, failing test"
	exit_code=$[exit_code + 1]
fi

if [[ pylint_violations!="" && pylint_violations -gt MAX_PYLINT_VIOLATIONS ]]; then
	echo "$pylint_violations is too many PyLint Violations, failing test (allowed $MAX_PYLINT_VIOLATIONS)"
	exit_code=$[exit_code + 1]
else
	echo "PyLint Violations = $pylint_violations: OK"
fi

if [[ pep8_violations!="" && pep8_violations -gt MAX_PEP8_VIOLATIONS ]]; then
	echo "$pep8_violations is too many PEP-8 Violations, failing test (allowed $MAX_PEP8_VIOLATIONS"	
	exit_code=$[exit_code + 1]
else
	echo "PEP-8 Violations = $pep8_violations: OK"
fi


exit $exit_code
