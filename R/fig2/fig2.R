# read tsv files
server_0_num = read.table(file = '~/DS/server_0_num.tsv', sep = '\t', header = TRUE)
server_1_num = read.table(file = '~/DS/server_1_num.tsv', sep = '\t', header = TRUE)

dataframe_server_0 = data.frame(server_0_num)
dataframe_server_1 = data.frame(server_1_num)

#Make arrays same length by adding zeros
dataframe_server_0[seq(nrow(dataframe_server_0), nrow(dataframe_server_1)),1] = 0

# adds them after instead of next
dataframe = rbind(dataframe_server_0=dataframe_server_0[seq(dataframe_server_0)], dataframe_server_1)

# adds them as 2 variables
dataframe2 = data.frame(dataframe_server_0, dataframe_server_1)

