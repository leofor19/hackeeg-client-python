    // FILEPATH: /c:/Users/leofo/OneDrive - McGill University/Documents McGill/Github/hackeeg-client-python-singleboard/hackeeg/driver.cpp

    #include <iostream>
    #include <vector>
    #include <unordered_set>

    class HackEEGDriver {
    public:
        std::vector<int> acquire_data(int max_samples, float duration, int speed, bool display_output = false) {
            if (max_samples == 0) {
                max_samples = max_samples_;
            }

            if (duration == 0) {
                duration = duration_;
            }

            if (speed == 0) {
                speed = speed_;
            }

            int max_sample_time = duration * speed;

            std::vector<int> samples;
            int sample_counter = 0;

            sdatac();
            rdatac();

            std::cout << "Flushing buffer..." << std::endl;
            flush_buffer(2, 4);

            std::cout << "Acquiring data..." << std::endl;
            double end_time = getCurrentTime();
            double start_time = getCurrentTime();
            while ((sample_counter < max_samples) && (sample_counter < max_sample_time)) {
                int result = read_rdatac_response();
                end_time = getCurrentTime();
                sample_counter++;
                if (mode_ == 2) {  // MessagePack mode
                    samples.push_back(result);
                } else {
                    process_sample(result, samples);
                }

                // optional display of samples
                if (display_output) {
                    std::cout << samples.back() << std::endl;
                }
            }

            dur_ = end_time - start_time;
            stop_and_sdatac_messagepack();
            samples = process_sample_batch(samples);

            return samples;
        }

        int find_dropped_samples(const std::vector<int>& samples, int number_of_samples) {
            std::unordered_set<int> sample_numbers;
            for (const auto& sample : samples) {
                sample_numbers.insert(get_sample_number(sample));
            }

            std::unordered_set<int> correct_sequence;
            for (int index = 0; index < number_of_samples; index++) {
                correct_sequence.insert(index);
            }

            std::vector<int> missing_samples;
            for (int sample_number : correct_sequence) {
                if (sample_numbers.find(sample_number) == sample_numbers.end()) {
                    missing_samples.push_back(sample_number);
                }
            }

            return missing_samples.size();
        }

        int get_sample_number(int sample) {
            // Extract the sample number from the given sample dictionary
            // and return it
            // ...
        }

    private:
        int max_samples_;
        float duration_;
        int speed_;
        int mode_;
        double dur_;

        void sdatac() {
            // Implementation of sdatac() function
            // ...
        }

        void rdatac() {
            // Implementation of rdatac() function
            // ...
        }

        void flush_buffer(int timeout, int flushing_levels) {
            // Implementation of flush_buffer() function
            // ...
        }

        int read_rdatac_response() {
            // Implementation of read_rdatac_response() function
            // ...
        }

        void process_sample(int result, std::vector<int>& samples) {
            // Implementation of process_sample() function
            // ...
        }

        void stop_and_sdatac_messagepack() {
            // Implementation of stop_and_sdatac_messagepack() function
            // ...
        }

        std::vector<int> process_sample_batch(const std::vector<int>& samples) {
            // Implementation of process_sample_batch() function
            // ...
        }

        double getCurrentTime() {
            // Implementation of getCurrentTime() function
            // ...
        }
    };
        """