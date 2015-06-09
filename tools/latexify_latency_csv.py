#!/usr/bin/env python3

"""
    Transform timestamp,a,b,c,d,e,f csv file to
    timestamp,a->b,a->c,a->d,... pairs, compute median and stdev,
    output to latex.
"""
import statistics
import csv
import sys
from collections import defaultdict


def main(input_file):
    latencies = get_latencies(input_file)
    statistical_properties = get_statistical_properties(latencies)
    latexify_properties(statistical_properties)

def get_latencies(input_file):
    # {
    #     'A': {
    #         'B': [
    #             (timestamp, latency_on_video_from_b_to_a)
    #         ]
    #     }
    # }
    latencies = defaultdict(lambda: defaultdict(list))
    with open(input_file) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            timestamp = row.pop('Timestamp')
            local_time = float(row.pop('Local time'))
            receiver = row.pop('Measurer')
            receiver_max = 0
            for role, value in row.items():
                value = float(value)
                if value > receiver_max:
                    receiver_max = value
                if value > (local_time if local_time > 1 else local_time + 60):
                    print('OBS: Possible erroneous reading at {}, local time was {:.3f}, measured value {:.3f}'.format(
                        timestamp, local_time, float(value)), file=sys.stderr)
            if any(float(value) for value in row.values() if float(value) > float(row[receiver])):
                print('Receiver not having highest reading, double check data for {} at {}'.format(
                    receiver, timestamp), file=sys.stderr)
                sys.exit(1)
            row.pop(receiver)
            for sender, value in row.items():
                if value:
                    latency = int(1000*(float(receiver_max) - float(value)))
                    if latency < 0:
                        print('Invalid reading between {} and {}: {} and {} (negative diff)'.format(
                            receiver, sender, receiver_max, value), file=sys.stderr)
                        sys.exit(1)
                    latencies[receiver][sender].append((timestamp, latency))
    return latencies


def get_statistical_properties(latencies):
    # creates a dict like {
    #     'A': {
    #         'B': (mean, stdev),
    #     }
    # }
    properties = defaultdict(dict)
    for receiver, sender_dict in latencies.items():
        for sender, measurements in sender_dict.items():
            values = [t[1] for t in measurements]
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            if any(value for value in values if abs(value - mean) > 2*stdev):
                print('OBS: Large offset at {}'.format(
                    str([(timestamp, value) for timestamp, value in measurements if abs(value - mean) > stdev])),
                    file=sys.stderr)

            # Ignore stdev if mean is too large to effectively visualize, as the error bars
            # are just in the way
            if mean > 1000:
                stdev = 0
            properties[receiver][sender] = (mean, stdev)
    return properties


def latexify_properties(properties, indent_level=0):
    indent_unit = ' '*4
    indent = indent_unit*indent_level
    for receiver in sorted(properties):
        print('%% Traffic going out to {}'.format(receiver))
        print('{0}\\addplot+[error bars/.cd,y dir=both, y explicit]\n{0}coordinates{{'.format(indent),
            end='')
        for sender in sorted(properties):
            mean, stdev = properties[receiver].get(sender, (0, 0))
            print('\n{indent}({sender},{value:.0f}) +- (0.0, {stdev:.0f})'.format(**{'sender': sender,
                'value': mean, 'stdev': stdev, 'indent': indent_unit*(indent_level+1)}), end='')

        print('};\n')

    print('\\legend{{{}}}'.format(', '.join(sorted(properties))))


if __name__ == '__main__':
    main(sys.argv[1])
