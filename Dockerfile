FROM alpine

LABEL maintainer="https://github.com/beteras/dockmirror"

RUN apk add --no-cache rsync

WORKDIR /home

CMD [ \
  "sh", \
  "-c", \
  " \
    echo dm: started; \
    echo dm: waiting 10s for first sync; \
    sleep 10; \
    \
    echo dm: looking for recent modified files; \
    while (find -mmin -15 | egrep '.*' > /dev/null); \
      do sleep 10; \
    done; \
    \
    echo dm: no recently modified files; \
    echo dm: exiting; \
  " \
]
