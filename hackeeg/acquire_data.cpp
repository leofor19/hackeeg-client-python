// acquire_data.cpp
// #include <vector>

// std::vector<int> acquire_data() {
//     std::vector<int> data;
//     // Acquire data...
//     return data;
// }

// FILEPATH: /c:/Users/leofo/OneDrive - McGill University/Documents McGill/Github/hackeeg-client-python-singleboard/hackeeg/driver.cpp

#include <chrono>
#include <iostream>
// #include <C:/src/vcpkg/packages/msgpack_x64-windows/include/msgpack.hpp>
#include <msgpack.hpp>
// #include <C:/src/vcpkg/installed/x64-windows/include/msgpack.hpp>
// #include <msgpack>
#include <vector>
// #include <unistd>
#include <unordered_set>
#include <tuple>


extern "C" {

std::vector<char> read_data_from_serial_port(int fd) {
    std::vector<char> buffer(38);
    ssize_t len = read(fd, buffer.data(), buffer.size());
    if (len == -1) {
        // Handle error
    }
    buffer.resize(len);
    return buffer;
}

}  // extern "C"

std::vector<msgpack::object> read_response(int fd) {
    msgpack::unpacker pac;
    std::vector<msgpack::object> unpacked_data;

    // Feed data into the unpacker
    std::string raw_data = read_data_from_serial_port(fd); // You need to implement this function

    // Check if we have enough data for unpacking
    if (raw_data.size() < 38) {
        // Discard the data and continue reading until we have enough data
        while (raw_data.size() < 38) {
            raw_data += read_data_from_serial_port(fd);
        }
    }

    pac.reserve_buffer(raw_data.size());
    memcpy(pac.buffer(), raw_data.data(), raw_data.size());
    pac.buffer_consumed(raw_data.size());

    // Unpack the data
    msgpack::object_handle oh;
    while(pac.next(oh)) {
        msgpack::object obj = oh.get();
        unpacked_data.push_back(obj);
    }

    return unpacked_data;
}

std::tuple<std::vector<std::vector<char>>, int, float> acquire_data_cpp(int max_samples, float duration, int speed, bool display_output = false, int fd) {
    if (max_samples == 0) {
        max_samples = this->max_samples;
    }

    if (duration == 0) {
        duration = this->duration;
    }

    if (speed == 0) {
        speed = this->speed;
    }

    int max_sample_time = duration * speed;

    std::vector<std::vector<char>> samples;
    int sample_counter = 0;

    // sdatac();
    // rdatac();

    // std::cout << "Flushing buffer..." << std::endl;
    // std::vector<int> result = flush_buffer(2, 4);
    // std::cout << "Acquiring data..." << std::endl;
    double end_time = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
    double start_time = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
    while ((sample_counter < max_samples) && (sample_counter < max_sample_time)) {
        std::vector<char> result = read_response(fd);
        end_time = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
        sample_counter++;
        samples.push_back(result);
        // if (mode == 2) {  // MessagePack mode
        //     samples.push_back(result);
        // } else {
        //     process_sample(result, samples);
        // }

        // optional display of samples
        if (display_output) {
            std::cout << samples.back() << std::endl;
        }
    }
    // double dur = (end_time - start_time) / 1000.0;
    // stop_and_sdatac_messagepack();
    // samples = process_sample_batch(samples);
    // return samples;

    return std::make_tuple(samples, sample_counter, end_time - start_time / 1000.0);
}


// int find_dropped_samples(std::vector<int> samples, int number_of_samples) {
//     std::unordered_set<int> sample_numbers;
//     for (int sample : samples) {
//         sample_numbers.insert(get_sample_number(sample));
//     }

//     std::unordered_set<int> correct_sequence;
//     for (int index = 0; index < number_of_samples; index++) {
//         correct_sequence.insert(index);
//     }

//     std::vector<int> missing_samples;
//     for (int sample_number : correct_sequence) {
//         if (sample_numbers.find(sample_number) == sample_numbers.end()) {
//             missing_samples.push_back(sample_number);
//         }
//     }

//     return missing_samples.size();
// }

// int get_sample_number(int sample) {
//     // Extract the sample number from the given sample dictionary
//     // and return it as an integer
//     // Implementation depends on the structure of the sample dictionary
//     // Replace the following line with the actual implementation
//     return sample["sample_number"];
// }
//     """